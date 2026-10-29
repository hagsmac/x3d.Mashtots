#!/usr/bin/env python3
"""Tokenizers for the Mashtots PoC.

* the token bill: big-lab tokenizers (tiktoken o200k / cl100k, and tokenizer.json files pinned by revision and sha256) on UDHR Armenian vs English and UD treebanks
* our arms, all with 32,000 entries except bytes:
    bytes             UTF-8 bytes (256 + <eos>)
    bpe               byte-level BPE with the GPT-style pre-split (the baseline every big lab uses)
    mashtots          character-level BPE over the Armenian letters with byte fallback (a letter is never cut into bytes) + morpheme pre-split
    bpe_morph         ablation: bpe + morpheme pre-split           (fertility only, no LM)
    mashtots_nomorph  ablation: mashtots without morpheme pre-split (fertility only, no LM)
* fertility (tokens per word), the UDHR ratio, stem-boundary recall against UD lemmas, the first Armenian merge
* encoding the E / W / G pools into uint16 token files for the trainer

usage: python3 -I mp_tok.py bill  --root DIR --out DIR [--allow-mirrors]
       python3 -I mp_tok.py train --root DIR [--sample-mb 300] [--vocab 32000]
       python3 -I mp_tok.py encode --root DIR [--workers N]
"""
from __future__ import annotations

import argparse
import collections
import functools
import glob
import json
import multiprocessing as mp
import os
import pathlib
import string
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mp_common as C  # noqa: E402
import mp_data as D  # noqa: E402

try:
    import regex as _re
    PIECE = _re.compile(r" ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+")
except ImportError:                                               # pragma: no cover
    import re as _re
    PIECE = _re.compile(r" ?[^\W\d_]+| ?\d+| ?[^\s\w]+|\s+(?!\S)|\s+")
SENT = D.PUA
GPT_SPLIT = r" ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"
ALL_ARMS = ["bytes", "bpe", "mashtots", "bpe_morph", "mashtots_nomorph"]

# ============================================================================ the big-lab tokenizers (the bill)
# (name, kind, repo or encoding, revision, sha256 of tokenizer.json measured on 2026-10-28 from the official file, mirror repo, mirror revision, deck key)
BILL_TOKENIZERS = [
    ("o200k (GPT-4o, gpt-oss)", "tiktoken", "o200k_base", None, None, None, None, "o200k"),
    ("Mistral Tekken (= Nemotron Nano 9B v2, Nemotron 3 Nano)", "hf", "mistralai/Mistral-Nemo-Instruct-2407", "04d8a90549d23fc6bd7f642064003592df51e9b3",
     "e11c71726323d33da7b8d6f6f269f1988931c0a52b7122bcdd8c05042974e0db", None, None, "tekken"),
    ("Nemotron Nano 9B v2", "hf", "nvidia/NVIDIA-Nemotron-Nano-9B-v2", "6533e8de2c68e4536bf7c411d7a3ce5734111476",
     "3277c00fe5fb3963b3cb7c07b7f183722d2af4d775a4aea7cfb3684d7cccbc2f", None, None, None),
    ("Gemma 3", "hf", "google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767",
     "4667f2089529e8e7657cfb6d1c19910ae71ff5f28aa7ab2ff2763330affad795", "unsloth/gemma-3-4b-it", "bf46152c47f5dd20b896357cb51abc4c03b8ee8c", "gemma"),
    ("DeepSeek V3", "hf", "deepseek-ai/DeepSeek-V3", "e815299b0bcbac849fa540c768ef21845365c9eb",
     "621ac2e32d0dba658404412318818aaa8ce8cda492e59830109d8da6b517fb41", None, None, "deepseek_v3"),
    ("Qwen 2.5", "hf", "Qwen/Qwen2.5-1.5B-Instruct", "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
     "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539", None, None, "qwen2.5"),
    ("Llama 3.2 (= Llama 3.1 vocabulary)", "hf", "meta-llama/Llama-3.2-3B-Instruct", "0cb88a4f764b7a12671c53f0838cd831a0843b95",
     "79e3e522635f3171300913bb421464a87de6222182a0570b9b2ccba2a964b2b4", "unsloth/Llama-3.2-3B-Instruct", "006f5dcd1393c3add266de40994ba96225e9689d", "llama3"),
    ("cl100k (GPT-4)", "tiktoken", "cl100k_base", None, None, None, None, "cl100k"),
]
# where the local dry run finds the same files (the census folder and the HF cache on this Mac)
LOCAL_TOKENIZER_FILES = {
    "mistralai/Mistral-Nemo-Instruct-2407": "{census}/tok-mistral-nemo/tokenizer.json",
    "nvidia/NVIDIA-Nemotron-Nano-9B-v2": "{census}/tok-nemotron-nano-9b-v2/tokenizer.json",
    "deepseek-ai/DeepSeek-V3": "{census}/tok-deepseek-v3/tokenizer.json",
    "google/gemma-3-4b-it": "{hf}/models--google--gemma-3-4b-it/snapshots/*/tokenizer.json",
    "Qwen/Qwen2.5-1.5B-Instruct": "{hf}/models--Qwen--Qwen2.5-1.5B-Instruct/snapshots/*/tokenizer.json",
    "meta-llama/Llama-3.2-3B-Instruct": "{hf}/models--meta-llama--Llama-3.2-3B-Instruct/snapshots/*/tokenizer.json",
}


def load_bill_tokenizer(spec, cache_dir, allow_mirrors=False):
    """Returns (count_fn, info) or (None, info) when the file cannot be had honestly."""
    name, kind, ref, rev, sha, mirror, mrev, _ = spec
    if kind == "tiktoken":
        import tiktoken
        enc = tiktoken.get_encoding(ref)
        return (lambda xs: [len(enc.encode_ordinary(x)) for x in xs]), dict(source=ref, vocab=enc.n_vocab, verified="tiktoken hash check")
    from tokenizers import Tokenizer
    path, how = None, ""
    if C.LOCAL:
        pat = LOCAL_TOKENIZER_FILES.get(ref, "").format(census=os.environ.get("MP_CENSUS_DIR", ""), hf=os.path.expanduser("~/.cache/huggingface/hub"))
        hits = glob.glob(pat)
        path, how = (hits[0], "local copy") if hits else (None, "not on this Mac")
    else:
        from huggingface_hub import hf_hub_download
        try:
            path = hf_hub_download(ref, "tokenizer.json", revision=rev, cache_dir=cache_dir, token=os.environ.get("HF_TOKEN") or None)
            how = f"{ref}@{rev[:8]}"
        except Exception as exc:
            how = f"official file unavailable ({type(exc).__name__}: gated? set HF_TOKEN after accepting the licence)"
            if allow_mirrors and mirror:
                try:
                    p = hf_hub_download(mirror, "tokenizer.json", revision=mrev, cache_dir=cache_dir)
                    if C.sha256_file(p) == sha:
                        path, how = p, f"mirror {mirror}@{mrev[:8]}, byte-identical to the official file (sha256 checked)"
                    else:
                        how += f"; mirror {mirror} differs from the official file, not used"
                except Exception as exc2:
                    how += f"; mirror failed ({type(exc2).__name__})"
    if not path:
        return None, dict(source=how)
    got = C.sha256_file(path)
    verified = "sha256 matches the official file" if got == sha else f"sha256 {got[:12]} differs from the recorded {sha[:12]} (the repo changed the file?)"
    t = Tokenizer.from_file(path)
    return (lambda xs: [len(e.ids) for e in t.encode_batch(xs, add_special_tokens=False)]), dict(source=how, vocab=t.get_vocab_size(), verified=verified)


def ud_test_sentences(root):
    out = {}
    for sid, (_, _, var) in D.UD.items():
        out[f"{var}:{sid}"] = [s["text"] for s in D.ud_sentences(root, sid, "test")]
    return out


def udhr_pair(root):
    d = pathlib.Path(os.environ.get("MP_UDHR_DIR", pathlib.Path(root) / "udhr"))
    return D.udhr_paragraphs(d / "udhr_hye.xml"), D.udhr_paragraphs(d / "udhr_eng.xml")


def fertility(count, sentences):
    n = np.array(count(sentences))
    w = np.array([len(s.split()) for s in sentences])
    rng = np.random.default_rng(405)
    idx = rng.integers(0, len(n), (400, len(n)))
    boot = n[idx].sum(1) / w[idx].sum(1)
    return dict(tok_per_word=round(float(n.sum() / w.sum()), 3), ci95=[round(float(np.percentile(boot, 2.5)), 3), round(float(np.percentile(boot, 97.5)), 3)],
                sentences=len(n), words=int(w.sum()))


def word_forms(sentences, per=10000):
    """Distinct word forms (lower case, punctuation stripped) among the first `per` running words: how many shapes one meaning takes."""
    words = []
    for s in sentences:
        words += [w.strip(string.punctuation + "«»՝՞՜՛։՚․…—–").lower() for w in s.split()]
        if len(words) >= per:
            break
    words = [w for w in words[:per] if w]
    return dict(running_words=len(words), distinct_forms=len(set(words)))


def bill(root, out, allow_mirrors=False):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    hy, en = udhr_pair(root)
    ud = ud_test_sentences(root)
    res = dict(grade="Measured", built=C.stamp(), udhr_paragraphs=[len(hy), len(en)], segmentation="every <para> of the preamble and the articles", rows={})
    for spec in BILL_TOKENIZERS:
        name, deck_key = spec[0], spec[7]
        count, info = load_bill_tokenizer(spec, str(out / "tok_cache"), allow_mirrors)
        row = dict(info=info, deck=C.DECK["token_bill_udhr_hy_over_en"]["values"].get(deck_key))
        if count is None:
            row["skipped"] = True
            print(f"  skipped {name}: {info['source']}")
        else:
            th, te = sum(count(hy)), sum(count(en))
            row.update(udhr_tokens=[th, te], udhr_ratio=round(th / te, 3), fertility={k: fertility(count, v) for k, v in ud.items()})
            print(f"  {name:<58} UDHR hy/en {th / te:5.2f}  (deck {row['deck']})  E {row['fertility']['E:ud_armtdp']['tok_per_word']:.2f} tok/word")
        res["rows"][name] = row
    res["word_forms"] = {k: word_forms(v) for k, v in ud.items()}
    res["word_forms"]["udhr_hy"] = word_forms(hy, per=10 ** 9)
    res["word_forms"]["udhr_en"] = word_forms(en, per=10 ** 9)
    C.dump_json(res, out / "token_bill.json")
    return res


# ============================================================================ morphemes
MIN_STEM, MAX_SUF, MAX_PEELS = 3, 7, 2
MORPH_POS = {"NOUN", "PROPN", "ADJ", "VERB", "AUX", "PRON", "DET", "NUM", "ADV"}

# Hand-written suffixes added to the inventory learned from the UD lemmas (see learn_suffixes). Lower case, without the stem.
# The learned list catches what is frequent in the treebanks; this list is where a speaker's knowledge goes: endings that are rare in news text but
# matter for Western Armenian and Grabar (for example the Western ablative and the Grabar plural cases). Kept short on purpose; edit freely.
HAND_SUFFIXES = [
    # Eastern: plural, cases, article, possessives
    "ներ", "եր", "ի", "ու", "ից", "ով", "ում", "ին", "ը", "ն", "ս", "դ", "ները", "երը", "ների", "երի", "ներից", "երից", "ներով", "երով", "ներում", "երում",
    "ություն", "ության", "ությունը", "ական", "ային", "ացի", "ավոր", "ություններ",
    # Western: ablative -էն, classical-spelling abstract nouns, plural forms
    "էն", "ներէն", "երէն", "ութիւն", "ութեան", "ութիւնը", "ներուն", "երուն", "ներու", "երու",
    # Grabar: plural nominative and accusative/genitive, instrumental
    "ք", "աց", "օք", "ովք", "ոյ", "ւոյ", "եան",
]


def learn_suffixes(root, min_count=8, top=600):
    """Suffixes = what a word form adds to the shared prefix with its lemma (UD train splits, all three varieties)."""
    cnt = collections.Counter()
    for sid in D.UD:
        for s in D.ud_sentences(root, sid, "train"):
            for form, lemma, upos in s["tokens"]:
                if upos not in MORPH_POS:
                    continue
                f, lm = form.lower(), lemma.lower()
                if not f or not all(C.is_armenian_char(ch) for ch in f):
                    continue
                k = len(os.path.commonprefix([f, lm]))
                if k >= 2 and len(f) > k and len(lm) - k <= 3 and 1 <= len(f) - k <= MAX_SUF:
                    cnt[f[k:]] += 1
    learned = [s for s, n in cnt.most_common(top) if n >= min_count]
    return learned, cnt


def gold_boundaries(root, split="test"):
    """(variety, word, stem-boundary char offset) from the UD lemmas: the gold standard the annotation task will replace."""
    out = []
    for sid, (_, _, var) in D.UD.items():
        for s in D.ud_sentences(root, sid, split):
            for form, lemma, upos in s["tokens"]:
                f, lm = form.lower(), lemma.lower()
                if upos not in MORPH_POS or not f or not all(C.is_armenian_char(ch) for ch in f):
                    continue
                k = len(os.path.commonprefix([f, lm]))
                if k >= 2 and len(f) > k and len(lm) - k <= 3:
                    out.append((var, form, k))
    return out


class Morph:
    def __init__(self, suffixes):
        self.suffixes = set(suffixes)
        self._split = functools.lru_cache(maxsize=1 << 20)(self._split_uncached)

    def split_morphemes(self, word):
        """Peels up to MAX_PEELS suffixes off the end of `word`, longest match first, keeping a stem of at least MIN_STEM letters.
        Returns the pieces in order, joined they give `word` back exactly (case preserved)."""
        low = word.lower()
        end, cuts = len(word), []
        for _ in range(MAX_PEELS):
            hit = 0
            for n in range(min(MAX_SUF, end - MIN_STEM), 0, -1):
                if low[end - n:end] in self.suffixes:
                    hit = n
                    break
            if not hit:
                break
            end -= hit
            cuts.append(end)
        cuts = sorted(cuts)
        return [word[a:b] for a, b in zip([0] + cuts, cuts + [len(word)])]

    def _split_uncached(self, piece):
        lead = piece[: len(piece) - len(piece.lstrip(" "))]
        core = piece[len(lead):]
        if not core or not all(C.is_armenian_char(ch) for ch in core):
            return (piece,)
        parts = self.split_morphemes(core)
        parts[0] = lead + parts[0]
        return tuple(parts)

    def presplit(self, text):
        """The text with the sentinel between pieces (word, punctuation, space runs; Armenian words cut at morpheme boundaries)."""
        out = []
        for m in PIECE.finditer(text):
            out.extend(self._split(m.group()))
        return SENT.join(out)


# ============================================================================ our tokenizers
def _special(byte_fallback):
    return ["<eos>"] + ([f"<0x{i:02X}>" for i in range(256)] if byte_fallback else [])


def build_tokenizer(arm, vocab, docs_iter, morph):
    from tokenizers import Regex, Tokenizer, decoders, models, pre_tokenizers, trainers
    if arm in ("bpe", "bpe_morph"):
        tok = Tokenizer(models.BPE())
        bl = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
        tok.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(SENT), "removed"), bl]) if arm == "bpe_morph" else bl
        tok.decoder = decoders.ByteLevel()
        tr = trainers.BpeTrainer(vocab_size=vocab, special_tokens=_special(False), initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
                                 show_progress=False, min_frequency=2)
    else:
        tok = Tokenizer(models.BPE(byte_fallback=True))
        if arm == "mashtots":
            tok.pre_tokenizer = pre_tokenizers.Split(Regex(SENT), "removed")
        else:
            tok.pre_tokenizer = pre_tokenizers.Split(Regex(GPT_SPLIT), "isolated")
        tok.decoder = decoders.Sequence([decoders.ByteFallback(), decoders.Fuse()])
        alphabet = list(C.LETTERS_38 + C.LETTERS_38_LOWER + C.ECH_YIWN + string.ascii_letters + string.digits + string.punctuation + " \n«»՝՞՜՛։՚․…—–")
        tr = trainers.BpeTrainer(vocab_size=vocab, special_tokens=_special(True), initial_alphabet=alphabet, limit_alphabet=400,
                                 show_progress=False, min_frequency=2)
    pre = morph.presplit if arm in ("mashtots", "bpe_morph") else (lambda t: t)
    tok.train_from_iterator((pre(t) for t in docs_iter()), tr)
    return tok


class Encoder:
    """One interface for every arm: encode(text) -> ids, byte-exact by construction (checked by roundtrip())."""

    def __init__(self, arm, path=None, morph=None):
        self.arm = arm
        self.morph = morph
        if arm == "bytes":
            self.tok, self.vocab_size, self.eos = None, 257, 256
        else:
            from tokenizers import Tokenizer
            self.tok = Tokenizer.from_file(str(path))
            self.vocab_size = self.tok.get_vocab_size()
            self.eos = self.tok.token_to_id("<eos>")

    def _pre(self, t):
        return self.morph.presplit(t) if self.arm in ("mashtots", "bpe_morph") else t

    def encode(self, text):
        if self.tok is None:
            return list(text.encode("utf-8"))
        return self.tok.encode(self._pre(text), add_special_tokens=False).ids

    def encode_batch(self, texts):
        if self.tok is None:
            return [list(t.encode("utf-8")) for t in texts]
        return [e.ids for e in self.tok.encode_batch([self._pre(t) for t in texts], add_special_tokens=False)]

    def token_bytes(self, ids):
        """Byte length of every token (letter-level maps and boundary scores need it)."""
        if self.tok is None:
            return [1] * len(ids)
        out = []
        for i in ids:
            s = self.tok.id_to_token(i)
            if self.arm in ("bpe", "bpe_morph"):
                out.append(len(s))                                   # byte-level: one character per byte
            elif s.startswith("<0x") and len(s) == 6:
                out.append(1)
            else:
                out.append(len(s.encode("utf-8")))
        return out

    def decode(self, ids):
        if self.tok is None:
            return bytes(ids).decode("utf-8", errors="replace")
        return self.tok.decode(ids, skip_special_tokens=False)

    def roundtrip(self, texts):
        bad = 0
        for t in texts:
            ids = self.encode(t)
            if self.decode(ids) != t or sum(self.token_bytes(ids)) != len(t.encode("utf-8")):
                bad += 1
        return bad


def tok_dir(root):
    return pathlib.Path(root) / "tokenizers"


def load_morph(root):
    d = C.load_json(tok_dir(root) / "suffixes.json")
    return Morph(d["inventory"])


def load_encoder(root, arm):
    morph = load_morph(root) if arm in ("mashtots", "bpe_morph") else None
    return Encoder(arm, None if arm == "bytes" else tok_dir(root) / f"{arm}.json", morph)


def balanced_sample(root, mb):
    """Equal Eastern and Western bytes (the owner's equal weighting), Grabar at 10%; deterministic."""
    target = {"E": 0.45 * mb * 1e6, "W": 0.45 * mb * 1e6, "G": 0.10 * mb * 1e6}
    out = []
    for v in "EWG":
        n = 0
        p = pathlib.Path(root) / "pools" / f"{v}.jsonl"
        if not p.exists():
            continue
        for r in D.read_jsonl(p):
            out.append(r["t"])
            n += len(r["t"].encode())
            if n >= target[v]:
                break
    return out


def train_all(root, vocab=C.VOCAB, sample_mb=300):
    root = pathlib.Path(root)
    tok_dir(root).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    learned, cnt = learn_suffixes(root)
    inventory = sorted(set(learned) | set(HAND_SUFFIXES), key=lambda s: (-len(s), s))
    C.dump_json(dict(inventory=inventory, learned=learned, hand=HAND_SUFFIXES, counts=dict(cnt.most_common(600)),
                     rule=f"longest suffix first, up to {MAX_PEELS} peels, stem >= {MIN_STEM} letters"), tok_dir(root) / "suffixes.json")
    morph = Morph(inventory)
    sample = balanced_sample(root, sample_mb)
    vocab = min(vocab, 32000) if not C.LOCAL else min(vocab, 2000)
    report = dict(vocab=vocab, sample_mb=round(sum(len(t.encode()) for t in sample) / 1e6, 1), suffixes=len(inventory), arms={})
    print(f"tokenizer sample {report['sample_mb']} MB (E:W:G = 45:45:10), {len(inventory)} suffixes ({len(learned)} learned + hand list)")
    for arm in ALL_ARMS[1:]:
        t1 = time.time()
        tok = build_tokenizer(arm, vocab, lambda: iter(sample), morph)
        tok.save(str(tok_dir(root) / f"{arm}.json"))
        report["arms"][arm] = dict(vocab=tok.get_vocab_size(), seconds=round(time.time() - t1, 1), first_armenian_merges=first_merges(tok, arm))
        print(f"  {arm:<18} vocab {tok.get_vocab_size():>6}  {time.time() - t1:5.0f} s  first Armenian merges: {report['arms'][arm]['first_armenian_merges'][:5]}")
    C.dump_json(report, tok_dir(root) / "train_report.json")
    print(f"tokenizers trained in {time.time() - t0:.0f} s")
    return report


def first_merges(tok, arm, k=10):
    """The first k merges that join two or more characters, at least one Armenian (byte-level merges inside one letter are skipped)."""
    m = json.loads(tok.to_str())["model"].get("merges", [])
    out = []
    for pair in m:
        a, b = pair if isinstance(pair, list) else pair.split(" ", 1)
        s = a + b
        if arm in ("bpe", "bpe_morph"):
            s = _bytelevel_to_text(s)
        if "\ufffd" not in s and len(s.strip()) >= 2 and any(C.is_armenian_char(ch) for ch in s):
            out.append(s)
            if len(out) >= k:
                break
    return out


@functools.lru_cache(maxsize=1)
def _byte_decoder():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs, n = bs[:], 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {chr(c): b for b, c in zip(bs, cs)}


def _bytelevel_to_text(s):
    dec = _byte_decoder()
    return bytes(dec.get(ch, 63) for ch in s).decode("utf-8", errors="replace")


# ============================================================================ fertility of our arms and boundary scores
def our_fertility(root, out):
    root = pathlib.Path(root)
    ud = ud_test_sentences(root)
    hy, en = udhr_pair(root)
    gold = gold_boundaries(root)
    res = dict(grade="Measured", arms={})
    for arm in ALL_ARMS:
        enc = load_encoder(root, arm)
        count = lambda xs, e=enc: [len(i) for i in e.encode_batch(xs)]
        row = dict(vocab=enc.vocab_size, fertility={k: fertility(count, v) for k, v in ud.items()})
        th, te = sum(count(hy)), sum(count(en))
        row["udhr_tokens"], row["udhr_ratio"] = [th, te], round(th / te, 3)
        row["roundtrip_failures"] = enc.roundtrip([s for v in ud.values() for s in v[:300]] + hy + list(C.PROBES.values()))
        row["boundary"] = boundary_scores(enc, gold)
        row["probes"] = {k: probe_pieces(enc, t) for k, t in C.PROBES.items()}
        res["arms"][arm] = row
        b = row["boundary"]
        print(f"  {arm:<18} E {row['fertility']['E:ud_armtdp']['tok_per_word']:.2f}  W {row['fertility']['W:ud_hyw']['tok_per_word']:.2f}  "
              f"G {row['fertility']['G:ud_caval']['tok_per_word']:.2f} tok/word | UDHR hy/en {row['udhr_ratio']:.2f} | stem-boundary recall "
              f"E {b['E']['recall']:.2f}/{b['E']['precision']:.2f} W {b['W']['recall']:.2f}/{b['W']['precision']:.2f} (recall/precision) | roundtrip failures {row['roundtrip_failures']}")
    C.dump_json(res, pathlib.Path(out) / "our_tokenizers.json")
    return res


def boundary_scores(enc, gold, per_variety=4000):
    by = collections.defaultdict(list)
    for var, word, k in gold:
        if len(by[var]) < per_variety:
            by[var].append((word, k))
    out = {}
    for var, items in by.items():
        hits = toks = ncuts = 0
        for word, k in items:
            ids = enc.encode(" " + word)
            lens = enc.token_bytes(ids)
            cuts, pos = set(), 0
            for n in lens[:-1]:
                pos += n
                cuts.add(pos)
            gold_byte = 1 + len(word[:k].encode("utf-8"))           # the leading space is one byte
            hits += gold_byte in cuts
            toks += len(ids)
            ncuts += len(cuts - {1})                                   # the cut after the leading space is not a word-internal cut
        rec, prec = hits / max(1, len(items)), hits / max(1, ncuts)
        out[var] = dict(words=len(items), recall=round(rec, 4), precision=round(prec, 4), f1=round(2 * rec * prec / max(1e-9, rec + prec), 4),
                        tokens_per_word=round(toks / max(1, len(items)), 3))
    return out


def probe_pieces(enc, text):
    ids = enc.encode(text)
    lens = enc.token_bytes(ids)
    b = text.encode("utf-8")
    pieces, pos = [], 0
    for n in lens:
        pieces.append(b[pos:pos + n].decode("utf-8", errors="replace"))
        pos += n
    return dict(tokens=len(ids), pieces=pieces)


# ============================================================================ encode the pools for the trainer
_E = {}


def _enc_init(root, arm):
    os.environ["TOKENIZERS_PARALLELISM"] = "false"           # one process per CPU already
    _E["enc"] = load_encoder(root, arm)


def _enc_batch(texts):
    enc = _E["enc"]
    out = []
    for ids in enc.encode_batch(texts):
        out.extend(ids)
        out.append(enc.eos)
    return np.asarray(out, dtype=np.uint16).tobytes()


def encode_pools(root, arms=("bytes", "bpe", "mashtots"), workers=None):
    root = pathlib.Path(root)
    workers = workers or max(1, min(46, (os.cpu_count() or 2) - 2))
    report = C.load_json(root / "tokens" / "encode_report.json", {})
    for arm in arms:
        for v in "EWG":
            src = root / "pools" / f"{v}.jsonl"
            dst = root / "tokens" / arm / f"{v}.bin"
            if dst.exists() and report.get(f"{arm}/{v}", {}).get("done"):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            t0 = time.time()
            nbytes = 0
            if arm == "bytes":                                   # raw UTF-8, 0xFF (never valid in UTF-8) between documents; the trainer maps it to <eos>
                with open(dst, "wb") as fh:
                    for r in D.read_jsonl(src):
                        b = r["t"].encode("utf-8")
                        fh.write(b)
                        fh.write(b"\xff")
                        nbytes += len(b)
                ntok = dst.stat().st_size
                report[f"{arm}/{v}"] = dict(tokens=ntok, text_bytes=nbytes, bytes_per_token=round(nbytes / max(1, ntok), 3), dtype="uint8",
                                            seconds=round(time.time() - t0, 1), done=True)
                C.dump_json(report, root / "tokens" / "encode_report.json")
                print(f"  {arm:<9} {v}: {ntok:>13,} tokens  {nbytes / max(1, ntok):5.2f} bytes/token  {time.time() - t0:6.0f} s")
                continue

            def batches(n=512):
                nonlocal nbytes
                b = []
                for r in D.read_jsonl(src):
                    b.append(r["t"])
                    nbytes += len(r["t"].encode("utf-8"))
                    if len(b) >= n:
                        yield b
                        b = []
                if b:
                    yield b

            with open(dst, "wb") as fh:
                if workers > 1:
                    ctx = mp.get_context("fork") if hasattr(os, "fork") else mp.get_context()
                    with ctx.Pool(workers, initializer=_enc_init, initargs=(str(root), arm)) as pool:
                        for chunk in pool.imap(_enc_batch, batches(), chunksize=1):
                            fh.write(chunk)
                else:
                    _enc_init(str(root), arm)
                    for b in batches():
                        fh.write(_enc_batch(b))
            ntok = dst.stat().st_size // 2
            report[f"{arm}/{v}"] = dict(tokens=ntok, text_bytes=nbytes, bytes_per_token=round(nbytes / max(1, ntok), 3), dtype="uint16",
                                        seconds=round(time.time() - t0, 1), done=True)
            C.dump_json(report, root / "tokens" / "encode_report.json")
            print(f"  {arm:<9} {v}: {ntok:>13,} tokens  {nbytes / max(1, ntok):5.2f} bytes/token  {time.time() - t0:6.0f} s")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bill", "train", "fertility", "encode"])
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--allow-mirrors", action="store_true")
    ap.add_argument("--vocab", type=int, default=C.VOCAB)
    ap.add_argument("--sample-mb", type=float, default=300)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--arms", default="bytes,bpe,mashtots")
    a = ap.parse_args()
    out = a.out or os.path.join(a.root, "results")
    if a.cmd == "bill":
        bill(a.root, out, a.allow_mirrors)
    elif a.cmd == "train":
        train_all(a.root, a.vocab, a.sample_mb)
    elif a.cmd == "fertility":
        our_fertility(a.root, out)
    else:
        encode_pools(a.root, tuple(a.arms.split(",")), a.workers or None)


if __name__ == "__main__":
    main()
