#!/usr/bin/env python3
"""Tokenizer fertility census for Armenian registers. Usage: python3 -I census.py DATA_DIR OUT_DIR
Metric: tokens per whitespace-separated word of each UD `# text =` sentence (punctuation stays attached to its word); also tokens per 100 characters.
95% CI = bootstrap over sentences (1000 resamples, seed 405). UDHR ratio = Armenian tokens / English tokens over the same articles' paragraphs."""
import glob, json, os, re, sys
import numpy as np
import xml.etree.ElementTree as ET
from tokenizers import Tokenizer
import tiktoken

DATA, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
HF = os.path.expanduser("~/.cache/huggingface/hub")
def hf_snap(m): return glob.glob(f"{HF}/{m}/snapshots/*/tokenizer.json")[0]

TOK = {   # name -> (kind, path or encoding)
    "o200k (GPT-4o, gpt-oss)": ("tt", "o200k_base"), "gpt-oss-20b tokenizer.json": ("hf", f"{DATA}/tok-gpt-oss-20b/tokenizer.json"),
    "Mistral Nemo (Tekken)": ("hf", f"{DATA}/tok-mistral-nemo/tokenizer.json"),
    "Nemotron 3 Nano 30B": ("hf", f"{DATA}/tok-nemotron-3-nano/tokenizer.json"),
    "Nemotron Nano 9B v2": ("hf", f"{DATA}/tok-nemotron-nano-9b-v2/tokenizer.json"),
    "Gemma 3": ("hf", hf_snap("models--google--gemma-3-4b-it")), "DeepSeek V3": ("hf", f"{DATA}/tok-deepseek-v3/tokenizer.json"),
    "Qwen 2.5": ("hf", hf_snap("models--Qwen--Qwen2.5-1.5B-Instruct")), "Llama 3.2 (=3.1 vocab)": ("hf", hf_snap("models--meta-llama--Llama-3.2-3B-Instruct")),
    "cl100k (GPT-4)": ("tt", "cl100k_base"),
}
def make(kind, ref):
    if kind == "hf":
        t = Tokenizer.from_file(ref); return (lambda xs: [len(e.ids) for e in t.encode_batch(xs, add_special_tokens=False)]), t.get_vocab_size()
    e = tiktoken.get_encoding(ref); return (lambda xs: [len(e.encode_ordinary(x)) for x in xs]), e.n_vocab
ENC = {k: make(*v) for k, v in TOK.items()}

def sentences(d):
    out = []
    for f in sorted(glob.glob(f"{DATA}/{d}/*.conllu")):
        for line in open(f, encoding="utf-8"):
            if line.startswith("# text = "): out.append(line[9:].strip())
    return out
CORP = {"Eastern (ArmTDP)": "UD_Armenian-ArmTDP", "Eastern (BSUT)": "UD_Armenian-BSUT",
        "Western (ArmTDP)": "UD_Western_Armenian-ArmTDP", "Grabar (CAVaL)": "UD_Classical_Armenian-CAVaL"}
S = {k: sentences(v) for k, v in CORP.items()}
for k, v in S.items(): assert len(v) > 1000, (k, len(v))
words = {k: np.array([len(s.split()) for s in v]) for k, v in S.items()}
chars = {k: np.array([len(s) for s in v]) for k, v in S.items()}
rng = np.random.default_rng(405)

def udhr(l):
    r = ET.parse(f"{DATA}/udhr/udhr_{l}.xml").getroot(); ns = "{http://efele.net/udhr}"
    return [" ".join("".join(p.itertext()).split()) for tag in ("preamble", "article") for blk in r.iter(ns + tag) for p in blk.iter(ns + "para")]
UD_EN, UD_HY = udhr("eng"), udhr("hye")

res = {}
for name, (enc, vocab) in ENC.items():
    row = {"vocab": vocab}
    for c, sents in S.items():
        n = np.array(enc(sents)); w, ch = words[c], chars[c]
        idx = rng.integers(0, len(n), (1000, len(n)))
        boot = n[idx].sum(1) / w[idx].sum(1)
        row[c] = dict(tok_per_word=float(n.sum() / w.sum()), ci=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                      tok_per_100char=float(100 * n.sum() / ch.sum()), sentences=len(n), words=int(w.sum()))
    he, ee = sum(enc(UD_HY)), sum(enc(UD_EN)); row["udhr_ratio_vs_english"] = he / ee; row["udhr_tokens"] = [he, ee]
    res[name] = row
json.dump(res, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=1)

FOLDER = {"o200k (GPT-4o, gpt-oss)": (2.64, 1.51), "Mistral Nemo (Tekken)": (2.99, 1.74), "Gemma 3": (4.15, 2.67), "DeepSeek V3": (4.38, 2.87),
          "Qwen 2.5": (7.66, 5.41), "Llama 3.2 (=3.1 vocab)": (12.33, 8.73), "cl100k (GPT-4)": (14.07, 10.15)}
cs = list(CORP)
L = ["| tokenizer | vocab | " + " | ".join(cs) + " | UDHR hy/en | folder table (EA words, UDHR) |", "|---|---|" + "---|" * (len(cs) + 2)]
for name, r in sorted(res.items(), key=lambda kv: kv[1][cs[0]]["tok_per_word"]):
    cells = " | ".join("%.2f [%.2f-%.2f]" % (r[c]["tok_per_word"], *r[c]["ci"]) for c in cs)
    L.append(f"| {name} | {r['vocab']} | {cells} | {r['udhr_ratio_vs_english']:.2f}x | " + ("%.2f, %.2fx" % FOLDER[name] if name in FOLDER else "not in folder table") + " |")
open(f"{OUT}/results.md", "w").write("\n".join(L) + "\n")
print("\n".join(L)); print({c: (len(S[c]), int(words[c].sum())) for c in cs}, "udhr paras", len(UD_HY), len(UD_EN))
