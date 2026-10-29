#!/usr/bin/env python3
"""Train one model of the grid (one tokenizer arm x one size, with or without Grabar text), then score it on the held-out sets.

usage: python3 -I mp_train.py --root DATA --arm bpe --size 15M --out RUNDIR [--grabar] [--tokens N] [--mirror DRIVEDIR] [--bench-steps 30]

Mixture (PREREG.md section 3): every training sequence is drawn from the Western pool with probability p_W = min(0.5, 4 x W_tokens / T),
from the Grabar pool (only with --grabar) with p_G = min(0.25, 4 x G_tokens / T), else from the Eastern pool. So a Western or Grabar token is
seen at most about 4 times; whatever is left of the equal share is the measured gap that new Western text would close.
Resume-safe: a checkpoint is written every --ckpt-minutes (and mirrored to Drive with --mirror); a finished run (done.json) is skipped.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import shutil
import sys
import time

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mp_common as C  # noqa: E402
import mp_eval as E  # noqa: E402
import mp_model as M  # noqa: E402
import mp_tok as TK  # noqa: E402


class Mixture:
    def __init__(self, root, arm, T, grabar, seq, seed):
        self.seq = seq
        self.rng = np.random.default_rng(seed)
        self.pools = {}
        self.bytes_arm = arm == "bytes"
        dt = np.uint8 if self.bytes_arm else np.uint16             # bytes: raw UTF-8 with 0xFF between documents (mp_tok.encode_pools)
        for v in "EWG":
            p = pathlib.Path(root) / "tokens" / arm / f"{v}.bin"
            if p.exists() and p.stat().st_size > 2 * (seq + 2):
                self.pools[v] = np.memmap(p, dtype=dt, mode="r")
        n = {v: len(a) for v, a in self.pools.items()}
        pw = min(0.5, 4 * n.get("W", 0) / T) if "W" in n else 0.0
        pg = min(0.25, 4 * n.get("G", 0) / T) if (grabar and "G" in n) else 0.0
        self.p = {"E": 1 - pw - pg, "W": pw, "G": pg}
        self.p = {v: p for v, p in self.p.items() if p > 0 and v in self.pools}
        z = sum(self.p.values())
        self.p = {v: p / z for v, p in self.p.items()}
        self.epochs = {v: round(self.p[v] * T / max(1, n[v]), 3) for v in self.p}
        self.keys = list(self.p)
        self.probs = np.array([self.p[k] for k in self.keys])

    def batch(self, B, device):
        which = self.rng.choice(len(self.keys), size=B, p=self.probs)
        x = np.empty((B, self.seq + 1), dtype=np.int64)
        for i, w in enumerate(which):
            a = self.pools[self.keys[w]]
            o = int(self.rng.integers(0, len(a) - self.seq - 1))
            x[i] = a[o:o + self.seq + 1]
        if self.bytes_arm:
            x[x == 255] = 256
        t = torch.from_numpy(x)
        if device.startswith("cuda"):
            t = t.pin_memory().to(device, non_blocking=True)
        else:
            t = t.to(device)
        return t[:, :-1], t[:, 1:]


def pick_device(want):
    if want != "auto":
        return want
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def micro_batch(size, device):
    if not device.startswith("cuda"):
        return 4
    return {"6M": 64, "15M": 64, "40M": 32, "85M": 32, "150M": 32}.get(size, 16)


def save_ckpt(path, model, opt, step, mix, extra):
    tmp = pathlib.Path(str(path) + ".tmp")
    torch.save(dict(model=model.state_dict(), opt=opt.state_dict(), step=step, rng=mix.rng.bit_generator.state,
                    torch_rng=torch.get_rng_state(), extra=extra), tmp)
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--arm", required=True, choices=C.ARMS)
    ap.add_argument("--size", required=True, choices=list(C.SIZES))
    ap.add_argument("--out", required=True)
    ap.add_argument("--grabar", action="store_true")
    ap.add_argument("--tokens", type=float, default=0)
    ap.add_argument("--seq", type=int, default=C.SEQ_LEN)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--compile", action="store_true")
    ap.add_argument("--seed", type=int, default=405)
    ap.add_argument("--mirror", default="")
    ap.add_argument("--ckpt-minutes", type=float, default=15)
    ap.add_argument("--stop-at", type=float, default=0, help="unix time; stop cleanly (checkpoint) when reached")
    ap.add_argument("--bench-steps", type=int, default=0, help="only measure throughput for this many optimizer steps")
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "done.json").exists() and not a.bench_steps:
        print("already done:", out)
        return
    mirror = pathlib.Path(a.mirror) if a.mirror else None
    if mirror and (mirror / "ckpt.pt").exists() and not (out / "ckpt.pt").exists():
        shutil.copy(mirror / "ckpt.pt", out / "ckpt.pt")
        print("restored the checkpoint from", mirror)

    device = pick_device(a.device)
    torch.manual_seed(a.seed)
    enc = TK.load_encoder(a.root, a.arm)
    cfg = M.Config.for_size(a.size, vocab=enc.vocab_size if a.arm != "bytes" else 257, seq=a.seq)
    model = M.GPT(cfg).to(device)
    counts = model.param_counts()
    T = int(a.tokens or C.train_tokens(a.size, dict(tokens_override=None)))
    mix = Mixture(a.root, a.arm, T, a.grabar, a.seq, a.seed)
    btok = M.batch_tokens_for(a.size) if not C.LOCAL else 2048
    mb = micro_batch(a.size, device)
    accum = max(1, btok // (mb * a.seq))
    btok = accum * mb * a.seq
    steps = max(1, T // btok)
    lr = M.lr_for(cfg.d)
    warm = max(10, int(0.05 * steps))
    decay, no_decay = [], []
    for n_, p in model.named_parameters():
        (decay if p.dim() >= 2 else no_decay).append(p)
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": 0.1}, {"params": no_decay, "weight_decay": 0.0}], lr=lr, betas=(0.9, 0.95),
                            eps=1e-8, fused=device.startswith("cuda"))
    step = 0
    if (out / "ckpt.pt").exists() and not a.bench_steps:
        ck = torch.load(out / "ckpt.pt", map_location=device, weights_only=False)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["opt"])
        step = ck["step"]
        mix.rng.bit_generator.state = ck["rng"]
        torch.set_rng_state(ck["torch_rng"])
        print(f"resumed at step {step}/{steps}")
    fwd = torch.compile(model) if (a.compile and device.startswith("cuda")) else model
    dtype = torch.bfloat16
    fpt = M.flops_per_token(cfg, counts["non_embedding"])
    meta = dict(arm=a.arm, size=a.size, grabar=a.grabar, config=cfg.to_dict(), params=counts, tokens=T, steps=steps, batch_tokens=btok,
                micro_batch=mb, accum=accum, lr=lr, warmup=warm, mixture=mix.p, epochs_per_pool=mix.epochs, flops_per_token=fpt,
                total_flops=fpt * T, device=device, torch=torch.__version__, compile=bool(a.compile), version=C.VERSION, started=C.stamp())
    C.dump_json(meta, out / "meta.json")
    print(f"{a.arm}-{a.size}{'-G' if a.grabar else ''}: {counts['non_embedding'] / 1e6:.1f}M non-embedding params, {T / 1e6:.0f}M tokens, "
          f"{steps} steps x {btok} tokens, lr {lr:.2e}, mixture {({k: round(v, 3) for k, v in mix.p.items()})}, epochs {mix.epochs}")

    log = open(out / "train_log.jsonl", "a")
    t_last_ck = time.time()
    t0, tok_seen, bench_t0 = time.time(), 0, None
    model.train()
    total_steps = steps if not a.bench_steps else a.bench_steps + 3
    while step < total_steps:
        if a.bench_steps and step == 3:                         # the first steps include compilation
            if device.startswith("cuda"):
                torch.cuda.synchronize()
            bench_t0, tok_seen = time.time(), 0
        lr_now = lr * (step + 1) / warm if step < warm else lr * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * (step - warm) / max(1, steps - warm))))
        for g in opt.param_groups:
            g["lr"] = lr_now
        loss_acc = 0.0
        for _ in range(accum):
            x, y = mix.batch(mb, device)
            with torch.autocast(device_type=device.split(":")[0], dtype=dtype, enabled=device.startswith("cuda")):
                loss = fwd(x, y)["loss"] / accum
            loss.backward()
            loss_acc += float(loss.detach())
        gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        tok_seen += btok
        if not math.isfinite(loss_acc):
            print("non-finite loss at step", step)
            sys.exit(3)
        if step % 25 == 0 or step == total_steps:
            el = time.time() - (bench_t0 or t0)
            tps = tok_seen / max(1e-9, el)
            rec = dict(step=step, loss=round(loss_acc, 4), lr=lr_now, grad_norm=round(float(gn), 3), tok_per_s=round(tps), elapsed=round(time.time() - t0, 1))
            log.write(json.dumps(rec) + "\n")
            log.flush()
            if step % 100 == 0 or step == total_steps:
                eta = (steps - step) * btok / max(1, tps) / 60
                print(f"  step {step}/{steps}  loss {loss_acc:.3f}  {tps / 1e3:.0f}k tok/s  {tps * fpt / 1e12:.0f} TFLOP/s  ETA {eta:.0f} min", flush=True)
        if a.bench_steps:
            continue
        if time.time() - t_last_ck > a.ckpt_minutes * 60 or (a.stop_at and time.time() > a.stop_at):
            save_ckpt(out / "ckpt.pt", model, opt, step, mix, meta)
            if mirror:
                mirror.mkdir(parents=True, exist_ok=True)
                shutil.copy(out / "ckpt.pt", mirror / "ckpt.pt")
            t_last_ck = time.time()
            if a.stop_at and time.time() > a.stop_at:
                print(f"time budget reached at step {step}/{steps}; checkpoint saved, run this cell again to continue")
                sys.exit(4)
    if a.bench_steps:
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        el = time.time() - bench_t0
        tps = tok_seen / el
        C.dump_json(dict(arm=a.arm, size=a.size, tok_per_s=tps, tflops=tps * fpt / 1e12, flops_per_token=fpt, steps=a.bench_steps,
                         batch_tokens=btok, device=device, gpu=torch.cuda.get_device_name(0) if device.startswith("cuda") else "cpu",
                         peak_mem_gb=torch.cuda.max_memory_allocated() / 1e9 if device.startswith("cuda") else None), out / "bench.json")
        print(f"bench {a.arm}-{a.size}: {tps / 1e3:.0f}k tokens/s, {tps * fpt / 1e12:.0f} TFLOP/s")
        return
    train_s = time.time() - t0
    torch.save({k: v.to(torch.bfloat16) if v.is_floating_point() else v for k, v in model.state_dict().items()}, out / "model.pt")
    C.dump_json(cfg.to_dict(), out / "config.json")
    t1 = time.time()
    res = E.score_all(model, enc, a.root, device, a.seq)
    res.update(meta, train_seconds=round(train_s, 1), score_seconds=round(time.time() - t1, 1), finished=C.stamp(),
               final_loss=loss_acc)
    C.dump_json(res, out / "eval.json")
    C.dump_json(dict(finished=C.stamp()), out / "done.json")
    if (out / "ckpt.pt").exists():
        (out / "ckpt.pt").unlink()
    if mirror:
        mirror.mkdir(parents=True, exist_ok=True)
        for f in ("model.pt", "config.json", "eval.json", "meta.json", "train_log.jsonl", "done.json"):
            shutil.copy(out / f, mirror / f)
        if (mirror / "ckpt.pt").exists():
            (mirror / "ckpt.pt").unlink()
    print(f"done {C.run_id(a.arm, a.size, a.grabar)}: bpb E {res.get('bpb_E')}, W {res.get('bpb_W')}, G {res.get('bpb_G')}, "
          f"E+W equal {res.get('bpb_EW_equal')}  ({train_s / 60:.1f} min training)")


if __name__ == "__main__":
    main()
