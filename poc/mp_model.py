#!/usr/bin/env python3
"""A plain decoder-only transformer in PyTorch: RMSNorm, rotary positions, QK-norm, SwiGLU, PyTorch SDPA attention, tied embeddings.

Nothing exotic, so that the bits-per-byte numbers say something about the tokenizers and the data, not about tricks.
`forward(..., need_attn=True)` takes an explicit path that returns every head's attention matrix (for the X3D export).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

import mp_common as C


@dataclass
class Config:
    vocab: int
    d: int
    L: int
    H: int
    seq: int = C.SEQ_LEN
    hidden: int = 0

    def __post_init__(self):
        self.hidden = self.hidden or C.swiglu_hidden(self.d)

    @classmethod
    def for_size(cls, size, vocab, seq=C.SEQ_LEN):
        s = C.SIZES[size]
        return cls(vocab=vocab, d=s["d"], L=s["L"], H=s["H"], seq=seq)

    def to_dict(self):
        return asdict(self)


class RMSNorm(nn.Module):
    def __init__(self, d, eps=1e-6):
        super().__init__()
        self.w = nn.Parameter(torch.ones(d))
        self.eps = eps

    def forward(self, x):
        return self.w * (x.float() * torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + self.eps)).type_as(x)


def rope_cache(seq, hd, base=10000.0, device=None):
    inv = 1.0 / (base ** (torch.arange(0, hd, 2, device=device).float() / hd))
    t = torch.arange(seq, device=device).float()
    f = torch.outer(t, inv)
    return torch.cos(f), torch.sin(f)


def apply_rope(x, cos, sin):
    x1, x2 = x[..., 0::2], x[..., 1::2]
    T = x.shape[-2]
    c, s = cos[:T].to(x.dtype), sin[:T].to(x.dtype)
    return torch.stack((x1 * c - x2 * s, x1 * s + x2 * c), dim=-1).flatten(-2)


class Attention(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.H, self.hd = cfg.H, cfg.d // cfg.H
        self.qkv = nn.Linear(cfg.d, 3 * cfg.d, bias=False)
        self.o = nn.Linear(cfg.d, cfg.d, bias=False)
        self.qn, self.kn = RMSNorm(self.hd), RMSNorm(self.hd)

    def forward(self, x, cos, sin, need_attn=False):
        B, T, D = x.shape
        q, k, v = self.qkv(x).view(B, T, 3, self.H, self.hd).permute(2, 0, 3, 1, 4)
        q, k = apply_rope(self.qn(q), cos, sin), apply_rope(self.kn(k), cos, sin)
        if need_attn:
            att = (q.float() @ k.float().transpose(-1, -2)) / math.sqrt(self.hd)
            att = att.masked_fill(torch.ones(T, T, dtype=torch.bool, device=x.device).triu(1), float("-inf")).softmax(-1)
            y = (att.to(v.dtype) @ v)
        else:
            att = None
            y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return self.o(y.transpose(1, 2).reshape(B, T, D)), att


class Block(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.n1, self.n2 = RMSNorm(cfg.d), RMSNorm(cfg.d)
        self.attn = Attention(cfg)
        self.w12 = nn.Linear(cfg.d, 2 * cfg.hidden, bias=False)
        self.w3 = nn.Linear(cfg.hidden, cfg.d, bias=False)

    def forward(self, x, cos, sin, need_attn=False):
        a, att = self.attn(self.n1(x), cos, sin, need_attn)
        x = x + a
        g, u = self.w12(self.n2(x)).chunk(2, dim=-1)
        return x + self.w3(F.silu(g) * u), att


class GPT(nn.Module):
    def __init__(self, cfg: Config):
        super().__init__()
        self.cfg = cfg
        self.emb = nn.Embedding(cfg.vocab, cfg.d)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.L))
        self.norm = RMSNorm(cfg.d)
        cos, sin = rope_cache(cfg.seq, cfg.d // cfg.H)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)
        self.apply(self._init)
        for b in self.blocks:                                    # scaled init of the residual projections
            nn.init.normal_(b.attn.o.weight, std=0.02 / math.sqrt(2 * cfg.L))
            nn.init.normal_(b.w3.weight, std=0.02 / math.sqrt(2 * cfg.L))

    @staticmethod
    def _init(m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, std=0.02)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, std=0.02)

    def forward(self, idx, targets=None, need_attn=False, need_hidden=False, reduction="mean"):
        x = self.emb(idx)
        attns, hiddens = [], []
        for b in self.blocks:
            x, att = b(x, self.cos, self.sin, need_attn)
            if need_attn:
                attns.append(att)
            if need_hidden:
                hiddens.append(x)
        x = self.norm(x)
        logits = F.linear(x, self.emb.weight)                    # tied output embedding
        out = {"logits": logits}
        if targets is not None:
            out["loss"] = F.cross_entropy(logits.float().view(-1, logits.size(-1)), targets.reshape(-1), ignore_index=-1, reduction=reduction)
        if need_attn:
            out["attn"] = attns                                  # L x [B, H, T, T]
        if need_hidden:
            out["hidden"] = hiddens + [x]
        return out

    def param_counts(self):
        emb = self.emb.weight.numel()
        total = sum(p.numel() for p in self.parameters())
        return dict(total=total, embedding=emb, non_embedding=total - emb)


def flops_per_token(cfg: Config, non_embedding):
    """Training FLOPs per token (forward + backward): 6 N for the matrices, 6 V d for the tied logits, 6 L T d for attention scores."""
    return 6 * non_embedding + 6 * cfg.vocab * cfg.d + 6 * cfg.L * cfg.seq * cfg.d


def lr_for(d):
    return min(2e-3, 1.5e-3 * math.sqrt(512 / d))


def batch_tokens_for(size):
    return {"tiny": 4096, "6M": 131072, "15M": 131072, "40M": 262144, "85M": 524288, "150M": 524288}[size]
