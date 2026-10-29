#!/usr/bin/env python3
"""Data for the Mashtots PoC: the source registry (licence, provenance, size), fetching, reading, the variety classifier, the orthography score,
cleaning, deduplication, decontamination and the Eastern / Western / Grabar pools.

usage:
  python3 -I mp_data.py plan  --profile smoke [--extra hplt,culturax,glotcc_hye,fw2_hye]       # the download list, nothing fetched
  python3 -I mp_data.py fetch --profile smoke --root DIR [--extra ...]                          # downloads (the notebook asks for approval first)
  python3 -I mp_data.py build --profile smoke --root DIR [--workers N]                          # eval sets, pools, data_stats.json
Local dry run: MP_LOCAL=1 and MP_UD_DIR=<folder with the four UD treebanks>; nothing is downloaded.
"""
from __future__ import annotations

import argparse
import collections
import glob
import gzip
import hashlib
import json
import math
import multiprocessing as mp
import os
import pathlib
import re
import sys
import time
import unicodedata
import urllib.request
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mp_common as C  # noqa: E402

UD_TAG = "r2.18"
UD = {  # id: (repo, prefix, variety)
    "ud_armtdp": ("UD_Armenian-ArmTDP", "hy_armtdp", "E"),
    "ud_bsut": ("UD_Armenian-BSUT", "hy_bsut", "E"),
    "ud_hyw": ("UD_Western_Armenian-ArmTDP", "hyw_armtdp", "W"),
    "ud_caval": ("UD_Classical_Armenian-CAVaL", "xcl_caval", "G"),
}
MB = 1e6

# Every source: what it is, its licence, where it comes from, how big the download is, what it is used for, and from which profile tier on.
# tier 0 = smoke, 1 = core, 2 = full, 3 = optional (only with --extra). Sizes are the files' sizes on Hugging Face / GitHub on 2026-10-28.
SOURCES = [
    dict(id="ud_armtdp", name="UD Armenian ArmTDP (Eastern)", kind="ud", licence="CC BY-SA 4.0", variety="E", role="train split + eval (test) + classifier + morph gold",
         url="https://github.com/UniversalDependencies/UD_Armenian-ArmTDP", size=14.0 * MB, tier=0),
    dict(id="ud_bsut", name="UD Armenian BSUT (Eastern)", kind="ud", licence="CC BY-SA 4.0", variety="E", role="train split + eval (test) + classifier",
         url="https://github.com/UniversalDependencies/UD_Armenian-BSUT", size=6.1 * MB, tier=0),
    dict(id="ud_hyw", name="UD Western Armenian ArmTDP", kind="ud", licence="CC BY-SA 4.0", variety="W", role="train split + eval (test) + classifier + morph gold",
         url="https://github.com/UniversalDependencies/UD_Western_Armenian-ArmTDP", size=16.1 * MB, tier=0),
    dict(id="ud_caval", name="UD Classical Armenian CAVaL (Grabar Gospels)", kind="ud", licence="CC BY-NC-SA 4.0 (non-commercial)", variety="G",
         role="Grabar train split (+G arm only) + eval (test) + classifier", url="https://github.com/UniversalDependencies/UD_Classical_Armenian-CAVaL", size=12.5 * MB, tier=0),
    dict(id="udhr", name="UDHR, Armenian and English (embedded in the notebook)", kind="embedded", licence="UN text, free to reproduce", variety="E",
         role="token bill only (excluded from training by decontamination)", url="https://github.com/eric-muller/udhr", size=0.044 * MB, tier=0),
    dict(id="armweb_val", name="ArmWeb validation split", kind="hf", repo="COPA-AI/armweb", rev="804790c6cd783532641b76e27381f92695505ce4",
         files=[("data/validation/part-0000.parquet", 14602616)], licence="ODC-By 1.0", variety="E", role="smoke-profile Eastern training text",
         url="https://huggingface.co/datasets/COPA-AI/armweb", tier=0, smoke_only=True),
    dict(id="armweb_test", name="ArmWeb test_iid split", kind="hf", repo="COPA-AI/armweb", rev="804790c6cd783532641b76e27381f92695505ce4",
         files=[("data/test_iid/part-0000.parquet", 14728943)], licence="ODC-By 1.0", variety="E", role="eval (Eastern, news)",
         url="https://huggingface.co/datasets/COPA-AI/armweb", tier=0),
    dict(id="wiki_hyw", name="Western Armenian Wikipedia (20231101.hyw)", kind="hf", repo="wikimedia/wikipedia", rev="b04c8d1ceb2f5cd4588862100d08de323dccfbaa",
         files=[("20231101.hyw/train-00000-of-00001.parquet", 27450541)], licence="CC BY-SA 3.0 / GFDL", variety="W",
         role="Western training text; 2% of articles held out for eval", url="https://huggingface.co/datasets/wikimedia/wikipedia", tier=0),
    dict(id="fw2_hyw_test", name="FineWeb-2 hyw_Armn test split", kind="hf", repo="HuggingFaceFW/fineweb-2", rev="af9c13333eb981300149d5ca60a8e9d659b276b9",
         files=[("data/hyw_Armn/test/000_00000.parquet", 2522946)], licence="ODC-By 1.0 (+ Common Crawl terms)", variety="W", role="eval (Western, web)",
         url="https://huggingface.co/datasets/HuggingFaceFW/fineweb-2", tier=0),
    dict(id="multiblimp", name="MultiBLiMP hye + hyw (minimal pairs)", kind="hf", repo="jumelet/multiblimp", rev="de923efa8d2483d6b13364ee68e65308e990a991",
         files=[("hye/data.tsv", 2594266), ("hyw/data.tsv", 2215960)], licence="CC BY 4.0", variety="E+W", role="eval only (grammaticality pairs)",
         url="https://huggingface.co/datasets/jumelet/multiblimp", tier=0),
    dict(id="armweb", name="ArmWeb train (COPA-AI, decontaminated news 2011-2026)", kind="hf", repo="COPA-AI/armweb", rev="804790c6cd783532641b76e27381f92695505ce4",
         files=[(f"data/train/part-{i:04d}.parquet", s) for i, s in enumerate(
             [340994221, 335740106, 346435909, 354216715, 350697530, 358599315, 374610140, 360744678, 237431856])],
         tier_files={1: 5, 2: 9}, licence="ODC-By 1.0", variety="E (+ some W)", role="main Eastern training text",
         url="https://huggingface.co/datasets/COPA-AI/armweb", tier=1),
    dict(id="wiki_hy", name="Armenian Wikipedia (20231101.hy)", kind="hf", repo="wikimedia/wikipedia", rev="b04c8d1ceb2f5cd4588862100d08de323dccfbaa",
         files=[("20231101.hy/train-00000-of-00003.parquet", 97014102), ("20231101.hy/train-00001-of-00003.parquet", 126836819),
                ("20231101.hy/train-00002-of-00003.parquet", 266270199)], licence="CC BY-SA 3.0 / GFDL", variety="E", role="Eastern training text",
         url="https://huggingface.co/datasets/wikimedia/wikipedia", tier=1),
    dict(id="pd_lit", name="Public-domain Armenian literature (EANC library; mislabelled 'classical' on HF: it is 19th-20th c. Eastern prose)",
         kind="hf", repo="catherinearnett/classical_armenian_pd", rev="3c82d695b7c6c366ec7d3e47cded592b000dc043",
         files=[("classical_armenian_pd.parquet", 24637701)], licence="CC0 1.0", variety="E (classical spelling likely)", role="Eastern training text (literary)",
         url="https://huggingface.co/datasets/catherinearnett/classical_armenian_pd", tier=1),
    dict(id="wikisource_hy", name="Armenian Wikisource (20231201.hy)", kind="hf", repo="wikimedia/wikisource", rev="f31a033f5f3d2107b3e864e578710df104a00baa",
         files=[("20231201.hy/train-00000-of-00001.parquet", 18574182)], licence="CC BY-SA 3.0 / GFDL (texts mostly public domain)", variety="mixed",
         role="training text routed by the classifier (the Grabar documents feed the +G arm)", url="https://huggingface.co/datasets/wikimedia/wikisource", tier=1),
    dict(id="fw2_hyw", name="FineWeb-2 hyw_Armn train", kind="hf", repo="HuggingFaceFW/fineweb-2", rev="af9c13333eb981300149d5ca60a8e9d659b276b9",
         files=[("data/hyw_Armn/train/000_00000.parquet", 264576419)], licence="ODC-By 1.0 (+ Common Crawl terms)", variety="W (GlotLID label)",
         role="main Western training text, re-labelled by our classifier", url="https://huggingface.co/datasets/HuggingFaceFW/fineweb-2", tier=1),
    dict(id="glotcc_hyw", name="GlotCC-V1 hyw-Armn", kind="hf", repo="cis-lmu/GlotCC-V1", rev="9ad140b6be3ac7b539606a2b4809b49d122823de",
         files=[("v1.0/hyw-Armn/hyw-Armn_0.parquet", 43721857)], licence="CC0 1.0 (+ Common Crawl terms)", variety="W (GlotLID label)",
         role="Western training text, re-labelled by our classifier", url="https://huggingface.co/datasets/cis-lmu/GlotCC-V1", tier=1),
    dict(id="fw2_hye_test", name="FineWeb-2 hye_Armn test split", kind="hf", repo="HuggingFaceFW/fineweb-2", rev="af9c13333eb981300149d5ca60a8e9d659b276b9",
         files=[("data/hye_Armn/test/000_00000.parquet", 22848292)], licence="ODC-By 1.0 (+ Common Crawl terms)", variety="E", role="eval (Eastern, web)",
         url="https://huggingface.co/datasets/HuggingFaceFW/fineweb-2", tier=1),
    dict(id="fw2_hye", name="FineWeb-2 hye_Armn train", kind="hf", repo="HuggingFaceFW/fineweb-2", rev="af9c13333eb981300149d5ca60a8e9d659b276b9",
         files=[("data/hye_Armn/train/000_00000.parquet", 2422275652)], licence="ODC-By 1.0 (+ Common Crawl terms)", variety="E",
         role="extra Eastern web text for the 85M and 150M runs (decontaminated by us; COPA measured 17% benchmark overlap before)",
         url="https://huggingface.co/datasets/HuggingFaceFW/fineweb-2", tier=2),
    dict(id="glotcc_hye", name="GlotCC-V1 hye-Armn", kind="hf", repo="cis-lmu/GlotCC-V1", rev="9ad140b6be3ac7b539606a2b4809b49d122823de",
         files=[("v1.0/hye-Armn/hye-Armn_0.parquet", 1457864000)], licence="CC0 1.0 (+ Common Crawl terms)", variety="E", role="optional Eastern web text",
         url="https://huggingface.co/datasets/cis-lmu/GlotCC-V1", tier=3),
    dict(id="hplt", name="HPLT 2.0 cleaned hye_Armn (first 8 of 44 shards)", kind="hf", repo="HPLT/HPLT2.0_cleaned", rev="d1324a5283f762ee62c2a5c81de08fc6450ea540",
         files=[(f"hye_Armn/train-{i:05d}-of-00044.parquet", 210 * MB) for i in range(8)], licence="CC0 1.0 (+ HPLT terms of use)", variety="E",
         role="optional Eastern web text (COPA measured 10.9% benchmark overlap)", url="https://huggingface.co/datasets/HPLT/HPLT2.0_cleaned", tier=3),
    dict(id="culturax", name="CulturaX hy (gated: accept its terms on Hugging Face first; needs HF_TOKEN)", kind="hf", repo="uonlp/CulturaX",
         rev="6a8734bc69fefcbb7735f4f9250f43e4cd7a442e", files=[("hy/hy_part_00000.parquet", 1877964316)], licence="mC4 (ODC-By) + OSCAR terms, gated",
         variety="E", role="optional Eastern web text", url="https://huggingface.co/datasets/uonlp/CulturaX", tier=3, gated=True),
]
SRC = {s["id"]: s for s in SOURCES}
NOT_AVAILABLE = [  # looked for on 2026-10-28, recorded so nobody looks again without reason
    ("NVIDIA Nemotron datasets (Nemotron-CC v2/v2.1, Nemotron-SFT-Multilingual v1/v2, Pretraining-Specialized)",
     "no Armenian: the CC sets are English-centric and the multilingual SFT sets list 5 to 6 other languages. Nemotron enters only through its tokenizer (= Mistral Tekken)."),
    ("Eastern Armenian National Corpus (EANC, ~110M tokens)", "search interface only; no bulk licence. Its public-domain library is the pd_lit source."),
    ("Matenadaran digitisations", "image access and rights are an institutional question (Church / institutions track)."),
    ("Grabar Bible beyond the UD Gospels, TITUS koriw", "licences unclear on HF and TITUS; not used until a rights holder agrees."),
    ("Diaspora newspapers (Aztag, Asbarez, Nor Haratch, Agos...)", "copyrighted; the participation track asks publishers for consent."),
]

EVAL_SETS = {  # name: (variety, how it is built)
    "E_armweb_test": ("E", "ArmWeb test_iid, first 4 MB of documents"),
    "E_ud_armtdp_test": ("E", "UD ArmTDP test split"),
    "E_ud_bsut_test": ("E", "UD BSUT test split"),
    "E_fw2_test": ("E", "FineWeb-2 hye test split, first 4 MB"),
    "W_fw2_test": ("W", "FineWeb-2 hyw test split (classifier-confirmed Western documents)"),
    "W_ud_hyw_test": ("W", "UD Western ArmTDP test split"),
    "W_wiki_heldout": ("W", "Western Wikipedia, articles whose id hash falls in the 2% hold-out"),
    "G_ud_caval_test": ("G", "UD CAVaL test split (Gospels)"),
}
EVAL_CAP = 4 * MB
PUA = "\ue000"   # the morpheme sentinel used by mp_tok (a private-use character); removed from all text here


# ======================================================================== planning and fetching
def selected(profile, extra=()):
    tier = C.LOCAL_PROFILE["sources_tier"] if profile == "local" else C.PROFILES[profile]["sources_tier"]
    out = []
    for s in SOURCES:
        if s.get("smoke_only") and tier > 0:
            continue
        if s["tier"] <= tier or s["id"] in extra:
            files = s.get("files")
            if files and s.get("tier_files"):
                files = files[: s["tier_files"].get(max(tier, 1), len(files))]
            out.append(dict(s, files=files))
    return out


def plan(profile, extra=()):
    rows, total = [], 0
    for s in selected(profile, extra):
        size = sum(f[1] for f in s["files"]) if s.get("files") else s.get("size", 0)
        if s["kind"] == "embedded":
            size = 0
        total += size
        rows.append(dict(id=s["id"], name=s["name"], licence=s["licence"], source=s["url"], files=len(s.get("files") or [1]), mb=round(size / MB, 1),
                         role=s["role"], gated=bool(s.get("gated"))))
    return rows, total


def print_plan(profile, extra=()):
    rows, total = plan(profile, extra)
    print(f"Downloads for profile '{profile}' (nothing has been fetched yet):")
    print(f"{'id':<14}{'MB':>9}  {'licence':<36} name")
    for r in rows:
        print(f"{r['id']:<14}{r['mb']:>9.1f}  {r['licence'][:35]:<36} {r['name']}" + ("  [GATED]" if r["gated"] else ""))
    print(f"{'total':<14}{total / MB:>9.1f} MB  ({total / 1e9:.2f} GB)")
    return rows, total


def _get(url, dest, retries=3):
    dest = pathlib.Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    for k in range(retries):
        try:
            tmp = dest.with_suffix(dest.suffix + ".part")
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mashtots-poc"}), timeout=120) as r, open(tmp, "wb") as fh:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    fh.write(b)
            tmp.replace(dest)
            return dest
        except Exception as exc:
            print(f"  retry {k + 1}: {url}: {exc}")
            time.sleep(3 * (k + 1))
    raise RuntimeError(f"could not download {url}")


def fetch(profile, root, extra=()):
    root = pathlib.Path(root)
    raw = root / "raw"
    log = []
    for s in selected(profile, extra):
        t0 = time.time()
        d = raw / s["id"]                                   # every source in its own directory
        if s["kind"] == "embedded":
            continue
        if s["kind"] == "ud":
            repo, prefix, _ = UD[s["id"]]
            for split in ("train", "dev", "test"):
                fn = f"{prefix}-ud-{split}.conllu"
                _get(f"https://raw.githubusercontent.com/UniversalDependencies/{repo}/{UD_TAG}/{fn}", d / fn)
        else:
            from huggingface_hub import hf_hub_download
            for fn, _size in s["files"]:
                hf_hub_download(s["repo"], fn, repo_type="dataset", revision=s["rev"], local_dir=str(d),
                                token=(os.environ.get("HF_TOKEN") or None) if s.get("gated") else None)
        got = sum(p.stat().st_size for p in d.rglob("*") if p.is_file() and ".cache" not in p.parts)
        print(f"  {s['id']:<14} {got / MB:8.1f} MB  {time.time() - t0:5.0f} s")
        log.append(dict(id=s["id"], bytes=got, seconds=round(time.time() - t0, 1), revision=s.get("rev", UD_TAG if s["kind"] == "ud" else "")))
    C.dump_json(log, root / "fetch_log.json")
    return log


# ======================================================================== readers
def ud_dir(root, sid):
    if C.LOCAL:
        repo = UD[sid][0]
        return pathlib.Path(os.environ.get("MP_UD_DIR", "")) / repo
    return pathlib.Path(root) / "raw" / sid


def read_conllu(path):
    """Yields sentences: dict(id, text, doc, tokens=[(form, lemma, upos)])."""
    sent, doc = None, ""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("# newdoc"):
                doc = line.split("=", 1)[-1].strip() if "=" in line else line
            elif line.startswith("# sent_id"):
                sent = dict(id=line.split("=", 1)[1].strip(), text="", doc=doc, tokens=[])
            elif line.startswith("# text =") and sent is not None:
                sent["text"] = line.split("=", 1)[1].strip()
            elif line and line[0].isdigit() and sent is not None:
                c = line.split("\t")
                if "-" in c[0] or "." in c[0]:
                    continue
                sent["tokens"].append((c[1], c[2], c[3]))
            elif not line and sent is not None:
                yield sent
                sent = None
    if sent is not None:
        yield sent


def ud_sentences(root, sid, split):
    prefix = UD[sid][1]
    p = ud_dir(root, sid) / f"{prefix}-ud-{split}.conllu"
    return list(read_conllu(p))


def ud_documents(sents, per_doc=25):
    """Groups sentences into documents: by newdoc where present, by book.chapter for CAVaL ids (MATT_6.1), else every `per_doc` sentences."""
    groups = collections.OrderedDict()
    for i, s in enumerate(sents):
        m = re.match(r"([A-Z]+_\d+)\.", s["id"])
        key = s["doc"] or (m.group(1) if m else f"chunk{i // per_doc}")
        groups.setdefault(key, []).append(s["text"])
    return [" ".join(v) for v in groups.values()]


def parquet_texts(path, max_bytes=None, field=None):
    """Yields (doc_id, text) from a parquet file, batch by batch; stops after max_bytes of text."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names
    if field is None:
        field = next((f for f in ("text", "content", "raw_content", "document") if f in names), None)
    if field is None:
        first = pf.read_row_group(0).slice(0, 1).to_pylist()[0]
        field = max((k for k, v in first.items() if isinstance(v, str)), key=lambda k: len(first[k]))
    idf = next((f for f in ("id", "doc_id", "url") if f in names), None)
    cols = [field] + ([idf] if idf and idf != field else [])
    seen, n = 0, 0
    for batch in pf.iter_batches(batch_size=2048, columns=cols):
        texts = batch.column(field).to_pylist()
        ids = batch.column(idf).to_pylist() if idf and idf != field else [None] * len(texts)
        for t, i in zip(texts, ids):
            n += 1
            if not t:
                continue
            yield (str(i) if i is not None else f"{pathlib.Path(path).stem}:{n}"), t
            seen += len(t.encode("utf-8"))
            if max_bytes and seen >= max_bytes:
                return


def source_files(root, sid):
    return sorted(str(p) for p in (pathlib.Path(root) / "raw" / sid).rglob("*.parquet") if ".cache" not in p.parts)


def source_docs(root, sid, max_bytes=None):
    budget = max_bytes
    for f in source_files(root, sid):
        for doc_id, text in parquet_texts(f, max_bytes=budget):
            yield doc_id, text
            if budget is not None:
                budget -= len(text.encode("utf-8"))
                if budget <= 0:
                    return


def read_multiblimp(path):
    """Rows of (good, bad, phenomenon) from a MultiBLiMP tsv, whatever the exact column names are."""
    import csv
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh, delimiter="\t")
        cols = rd.fieldnames or []
        good = next((c for c in cols if c.lower() in ("sen", "sentence", "good", "grammatical", "sen_good")), None)
        bad = next((c for c in cols if c.lower() in ("wrong_sen", "bad", "ungrammatical", "sen_bad", "wrong_sentence")), None)
        phen = next((c for c in cols if c.lower() in ("phenomenon", "feature", "type", "grammatical_feature")), None)
        if not good or not bad:
            raise ValueError(f"MultiBLiMP columns not recognised: {cols}")
        for r in rd:
            if r[good] and r[bad]:
                rows.append((r[good], r[bad], r.get(phen, "") if phen else ""))
    return rows


# ======================================================================== variety classifier and orthography score
def _grams(text, nmax=4, limit=1500):
    t = " " + re.sub(r"\s+", " ", text.lower()[:limit]) + " "
    for n in range(1, nmax + 1):
        for i in range(len(t) - n + 1):
            g = t[i:i + n]
            if g.strip() and any(C.is_armenian_char(ch) for ch in g):
                yield g


class VarietyNB:
    """Character 1-4-gram multinomial naive Bayes over E (Eastern), W (Western), G (Grabar), trained on the UD train splits.

    Caveat recorded in PREREG.md: the UD Western treebank is in classical spelling and the Eastern ones in reformed spelling, so the classifier
    may separate spelling rather than dialect. The orthography score below is reported beside it for exactly that reason.
    """
    classes = ("E", "W", "G")

    def __init__(self):
        self.logp, self.default, self.prior = {}, {}, {}

    def fit(self, docs_by_class, alpha=0.5, chars_per_class=4_000_000):
        counts = {c: collections.Counter() for c in self.classes}
        for c, docs in docs_by_class.items():
            used = 0
            for d in docs:
                counts[c].update(_grams(d, limit=10 ** 9))
                used += len(d)
                if used >= chars_per_class:
                    break
        vocab = set().union(*[set(v) for v in counts.values()])
        V = len(vocab)
        totals = {c: sum(counts[c].values()) for c in self.classes}
        for c in self.classes:
            self.default[c] = math.log(alpha / (totals[c] + alpha * V))
        for g in vocab:
            self.logp[g] = tuple(math.log((counts[c][g] + alpha) / (totals[c] + alpha * V)) for c in self.classes)
        n = sum(len(v) for v in docs_by_class.values())
        self.prior = {c: math.log(len(docs_by_class[c]) / n) for c in self.classes}
        return self

    def scores(self, text):
        s = [0.0, 0.0, 0.0]
        k = 0
        dflt = tuple(self.default[c] for c in self.classes)
        for g in _grams(text):
            lp = self.logp.get(g, dflt)
            s[0] += lp[0]
            s[1] += lp[1]
            s[2] += lp[2]
            k += 1
        return s, k

    def predict(self, text):
        s, k = self.scores(text)
        if k == 0:
            return "?", 0.0
        m = max(s)
        p = [math.exp(x - m) for x in s]
        z = sum(p)
        i = max(range(3), key=lambda j: s[j])
        return self.classes[i], p[i] / z

    def dump(self, path):
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            json.dump(dict(logp=self.logp, default=self.default, prior=self.prior), fh, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            d = json.load(fh)
        m = cls()
        m.logp = {k: tuple(v) for k, v in d["logp"].items()}
        m.default, m.prior = d["default"], d["prior"]
        return m


_CLASSICAL = [r"ութիւն", r"(?<![\w])եւ(?![\w])", r"իւ", r"եա", r"(?<=\w)է", r"(?<!ու)ոյ"]
_REFORMED = [r"ություն", r"և", r"յու", r"ույ"]
_CL = [re.compile(p) for p in _CLASSICAL]
_RF = [re.compile(p) for p in _REFORMED]


def orthography(text):
    """Classical vs reformed (1922/1940) spelling, from transparent markers. Returns (label, score in -1..1).

    classical markers: -ութիւն, the word եւ, իւ, եա, է inside a word, ոյ (not ույ); reformed markers: -ություն, և, յու, ույ.
    A heuristic, not a gold label: the annotation task collects the human label.
    """
    t = text.lower()[:4000]
    c = sum(len(p.findall(t)) for p in _CL)
    r = sum(len(p.findall(t)) for p in _RF)
    score = (c - r) / (c + r + 1)
    return ("classical" if score >= 0.3 else "reformed" if score <= -0.3 else "unclear"), round(score, 3)


# ======================================================================== cleaning, dedup, decontamination
_WS = re.compile(r"\s+")
_WORD = re.compile(r"[^\W\d_]+")


def clean(text):
    text = unicodedata.normalize("NFC", text).replace(PUA, " ").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def norm_hash(text):
    return hashlib.md5(_WS.sub(" ", text.lower()).strip().encode("utf-8")).digest()[:12]


def word_ngrams(text, n):
    w = _WORD.findall(text.lower())
    for i in range(len(w) - n + 1):
        yield zlib.crc32(" ".join(w[i:i + n]).encode("utf-8"))


def contam_keys(texts):
    """13-gram keys of long eval texts and 8-gram keys of short ones (UD sentences, minimal pairs, probes)."""
    k13, k8 = set(), set()
    for t in texts:
        nw = len(_WORD.findall(t))
        if nw >= 13:
            k13.update(word_ngrams(t, 13))
        if 8 <= nw < 40:
            k8.update(word_ngrams(t, 8))
    return k13, k8


_G = {}


def _init_worker(model_path, k13, k8, min_chars, min_share):
    _G.update(nb=VarietyNB.load(model_path), k13=k13, k8=k8, min_chars=min_chars, min_share=min_share)


def _process(batch):
    out = []
    for src, doc_id, text in batch:
        t = clean(text)
        if len(t) < _G["min_chars"]:
            out.append((src, doc_id, None, "short"))
            continue
        if C.armenian_share(t) < _G["min_share"]:
            out.append((src, doc_id, None, "not_armenian"))
            continue
        if any(h in _G["k13"] for h in word_ngrams(t, 13)) or (_G["k8"] and any(h in _G["k8"] for h in word_ngrams(t, 8))):
            out.append((src, doc_id, None, "contaminated"))
            continue
        lab, p = _G["nb"].predict(t)
        ortho, osc = orthography(t)
        out.append((src, doc_id, dict(t=t, v=lab, p=round(p, 3), o=ortho, os=osc, h=norm_hash(t).hex()), "ok"))
    return out


# ======================================================================== the build
def heldout(doc_id, pct=2):
    return zlib.crc32(str(doc_id).encode()) % 100 < pct


def write_jsonl(path, rows):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def build(profile, root, workers=None, extra=(), eastern_cap_gb=None):
    root = pathlib.Path(root)
    root.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    tier = C.LOCAL_PROFILE["sources_tier"] if profile == "local" else C.PROFILES[profile]["sources_tier"]
    have = {s["id"] for s in selected(profile, extra)}
    stats = dict(profile=profile, built=C.stamp(), version=C.VERSION, sources={}, eval={}, pools={}, classifier={}, crosstab={})

    # ---- 1. classifier from the UD train splits, scored on the UD test splits
    train_docs = {"E": [], "W": [], "G": []}
    for sid, (_, _, var) in UD.items():
        train_docs[var] += ud_documents(ud_sentences(root, sid, "train"), per_doc=5)
    nb = VarietyNB().fit(train_docs)
    nb.dump(root / "variety_nb.json.gz")
    conf = collections.Counter()
    for sid, (_, _, var) in UD.items():
        for snt in ud_sentences(root, sid, "test"):
            if len(snt["text"]) >= 20:
                conf[(var, nb.predict(snt["text"])[0])] += 1
    acc = {v: round(sum(n for (a, b), n in conf.items() if a == v and b == v) / max(1, sum(n for (a, _), n in conf.items() if a == v)), 4) for v in "EWG"}
    stats["classifier"] = dict(unit="single sentences (20+ characters) of the UD test splits", accuracy=acc,
                               confusion={f"{a}->{b}": n for (a, b), n in sorted(conf.items())}, grade="Measured")
    print("variety classifier on single UD test sentences: accuracy", acc)

    # ---- 2. evaluation sets (written first; everything later is decontaminated against them)
    ev = {}
    ev["E_ud_armtdp_test"] = ud_documents(ud_sentences(root, "ud_armtdp", "test"))
    ev["E_ud_bsut_test"] = ud_documents(ud_sentences(root, "ud_bsut", "test"))
    ev["W_ud_hyw_test"] = ud_documents(ud_sentences(root, "ud_hyw", "test"))
    ev["G_ud_caval_test"] = ud_documents(ud_sentences(root, "ud_caval", "test"))

    def capped(it, cap=EVAL_CAP):
        out, n = [], 0
        for _id, t in it:
            t = clean(t)
            if len(t) < 200 or C.armenian_share(t) < 0.6:
                continue
            out.append(t)
            n += len(t.encode())
            if n >= cap:
                break
        return out

    if "armweb_test" in have:
        ev["E_armweb_test"] = capped(source_docs(root, "armweb_test"))
    if "fw2_hye_test" in have:
        ev["E_fw2_test"] = capped(source_docs(root, "fw2_hye_test"))
    if "fw2_hyw_test" in have:
        docs = capped(source_docs(root, "fw2_hyw_test"), cap=10 ** 12)
        labs = collections.Counter(nb.predict(t)[0] for t in docs)
        stats["eval"]["fw2_hyw_test_labels"] = dict(labs)
        ev["W_fw2_test"] = [t for t in docs if nb.predict(t)[0] == "W"][:2000]
    if "wiki_hyw" in have:
        ev["W_wiki_heldout"] = [clean(t) for i, t in source_docs(root, "wiki_hyw") if heldout(i) and len(t) >= 200][:2000]
    ev = {k: v for k, v in ev.items() if v}
    for k, docs in ev.items():
        write_jsonl(root / "eval" / f"{k}.jsonl", [{"t": t} for t in docs])
        stats["eval"][k] = dict(variety=k[0], docs=len(docs), bytes=sum(len(t.encode()) for t in docs), how=EVAL_SETS.get(k, ("", ""))[1])
    mb_rows = {}
    if "multiblimp" in have or C.LOCAL:
        for lang in ("hye", "hyw"):
            p = root / "raw" / "multiblimp" / lang / "data.tsv"
            if p.exists():
                mb_rows[lang] = read_multiblimp(p)
                write_jsonl(root / "eval" / f"multiblimp_{lang}.jsonl", [dict(good=g, bad=b, phen=ph) for g, b, ph in mb_rows[lang]])
        stats["eval"]["multiblimp"] = {k: len(v) for k, v in mb_rows.items()}
    print("eval sets:", {k: v["docs"] for k, v in stats["eval"].items() if isinstance(v, dict) and "docs" in v})

    # ---- 3. decontamination keys: every eval text, the minimal pairs, the probes, the UDHR
    contam_texts = [t for docs in ev.values() for t in docs]
    contam_texts += [s for rows in mb_rows.values() for g, b, _ in rows for s in (g, b)]
    contam_texts += list(C.PROBES.values())
    contam_texts += ud_test_sentences(root)
    udhr = pathlib.Path(os.environ.get("MP_UDHR_DIR", root / "udhr")) / "udhr_hye.xml"
    if udhr.exists():
        contam_texts += udhr_paragraphs(udhr)
    k13, k8 = contam_keys(contam_texts)
    print(f"decontamination keys: {len(k13):,} 13-grams, {len(k8):,} 8-grams")

    # ---- 4. training documents from every source, cleaned, filtered, classified, deduplicated
    cap_e = (eastern_cap_gb or {0: 0.05, 1: 3.0, 2: 12.0}.get(tier, 12.0)) * 1e9          # per Eastern source

    def doc_stream():
        for sid, (_, _, var) in UD.items():
            for i, d in enumerate(ud_documents(ud_sentences(root, sid, "train"))):
                yield sid, f"{sid}:{i}", d
        for sid in ["armweb_val", "armweb", "wiki_hy", "pd_lit", "wikisource_hy", "wiki_hyw", "fw2_hyw", "glotcc_hyw", "fw2_hye", "glotcc_hye", "hplt", "culturax"]:
            if sid not in have or C.LOCAL:
                continue
            maxb = cap_e if SRC[sid]["variety"].startswith("E") else None
            if sid in ("fw2_hye", "glotcc_hye", "hplt", "culturax"):        # web extras: only what the 85M / 150M runs need beyond ArmWeb
                maxb = min(maxb or 3e9, 3e9)
            for doc_id, text in source_docs(root, sid, max_bytes=maxb):
                if sid == "wiki_hyw" and heldout(doc_id):
                    continue
                yield sid, doc_id, text

    pools = {v: open_pool(root, v) for v in "EWG"}
    seen = set()
    src_stats = collections.defaultdict(lambda: collections.Counter())
    cross = collections.Counter()
    workers = workers or max(1, min(46, (os.cpu_count() or 2) - 2))

    def batches(n=256):
        b = []
        for item in doc_stream():
            b.append(item)
            if len(b) >= n:
                yield b
                b = []
        if b:
            yield b

    args = (str(root / "variety_nb.json.gz"), k13, k8, 200, 0.6)
    if workers > 1:
        ctx = mp.get_context("fork") if hasattr(os, "fork") else mp.get_context()
        pool = ctx.Pool(workers, initializer=_init_worker, initargs=args)
        results = pool.imap(_process, batches(), chunksize=2)
    else:
        _init_worker(*args)
        pool, results = None, map(_process, batches())
    n_done = 0
    for res in results:
        for sid, doc_id, d, why in res:
            st = src_stats[sid]
            st["docs_in"] += 1
            if d is None:
                st[why] += 1
                continue
            if d["h"] in seen:
                st["duplicate"] += 1
                continue
            seen.add(d["h"])
            b = len(d["t"].encode("utf-8"))
            st["kept"] += 1
            st["bytes_kept"] += b
            st[f"label_{d['v']}"] += 1
            st[f"ortho_{d['o']}"] += 1
            cross[(d["v"], d["o"])] += b
            pools[d["v"] if d["v"] in pools else "E"].write(json.dumps(dict(t=d["t"], s=sid, o=d["o"]), ensure_ascii=False) + "\n")
            n_done += 1
        if n_done and n_done % 200000 < 256:
            print(f"  {n_done:,} documents kept, {time.time() - t0:.0f} s")
    if pool:
        pool.close()
        pool.join()
    for f in pools.values():
        f.close()
    for v in "EWG":
        p = root / "pools" / f"{v}.jsonl"
        stats["pools"][v] = dict(bytes=0, docs=0, by_source=collections.Counter())
        for r in read_jsonl(p):
            stats["pools"][v]["bytes"] += len(r["t"].encode("utf-8"))
            stats["pools"][v]["docs"] += 1
            stats["pools"][v]["by_source"][r["s"]] += len(r["t"].encode("utf-8"))
        stats["pools"][v]["by_source"] = dict(stats["pools"][v]["by_source"])
    stats["sources"] = {k: dict(v) for k, v in src_stats.items()}
    stats["crosstab_bytes"] = {f"{a}|{b}": n for (a, b), n in sorted(cross.items())}
    stats["seconds"] = round(time.time() - t0, 1)
    stats["grade"] = "Measured (this run's data)"
    C.dump_json(stats, root / "data_stats.json")
    try:
        annotation_sample(root)
    except Exception as exc:                                  # the batch is a by-product: never let it stop the data build
        print("annotation batch skipped:", exc)
    print("pools (MB):", {v: round(s["bytes"] / MB, 1) for v, s in stats["pools"].items()}, f"| {stats['seconds']} s")
    return stats


_SENT_SPLIT = re.compile(r"(?<=[։:.!?՞])\s+")


def annotation_sample(root, n_sent=240, n_words=120, seed=405):
    """A first annotation batch (participation/TASKS.md): sentences stratified over classifier variety x spelling for the dialect + spelling task,
    content words for the morpheme task, plus QC items whose answers go to a separate key file that is never given to annotators."""
    import random
    root = pathlib.Path(root)
    rng = random.Random(seed)
    cells = collections.defaultdict(list)
    for v in "EWG":
        p = root / "pools" / f"{v}.jsonl"
        if not p.exists():
            continue
        for k, r in enumerate(read_jsonl(p)):
            if k > 20000:
                break
            for snt in _SENT_SPLIT.split(r["t"])[:6]:
                nw = len(snt.split())
                if 8 <= nw <= 40 and C.armenian_share(snt) > 0.9:
                    cells[(v, r.get("o", "?"))].append((snt.strip(), r["s"]))
    items, key = [], {}
    per = max(1, n_sent // max(1, len(cells)))
    for (v, o), rows in sorted(cells.items()):
        for snt, src in rng.sample(rows, min(per, len(rows))):
            items.append(dict(task="dialect_spelling", text=snt, source=src))
    gold_words = []
    for sid, (_, _, var) in UD.items():
        try:
            for s_ in ud_sentences(root, sid, "test")[:400]:
                for form, lemma, upos in s_["tokens"]:
                    f, lm = form.lower(), lemma.lower()
                    k = len(os.path.commonprefix([f, lm]))
                    if upos in ("NOUN", "VERB", "ADJ") and len(f) >= 6 and k >= 2 and len(f) > k and len(lm) - k <= 3 and all(C.is_armenian_char(c) for c in f):
                        gold_words.append((form, k, s_["text"], var))
        except FileNotFoundError:
            pass
    rng.shuffle(gold_words)
    for form, k, ctx, var in gold_words[:n_words]:
        items.append(dict(task="morph", word=form, context=ctx, source=f"UD {var} test"))
    qc = []
    for sid, (_, _, var) in UD.items():                      # dialect QC: treebank sentences of known variety (spelling key only where unambiguous)
        try:
            sents = [x["text"] for x in ud_sentences(root, sid, "test") if 8 <= len(x["text"].split()) <= 30]
        except FileNotFoundError:
            continue
        for snt in rng.sample(sents, min(6, len(sents))):
            qc.append((dict(task="dialect_spelling", text=snt, source="QC"), dict(dialect=var, spelling=None)))
    rng.shuffle(items)
    out = []
    for i, it in enumerate(items):
        out.append(dict(it, id=f"b001-{i:04d}"))
    for j, (it, ans) in enumerate(qc):
        iid = f"b001-q{j:03d}"
        pos = rng.randrange(0, len(out) + 1)
        out.insert(pos, dict(it, id=iid))
        key[iid] = ans
    for it in out:                                            # morph items: the UD lemma split is the gold the annotators are scored against
        if it["task"] == "morph":
            k = next(kk for form, kk, ctx, var in gold_words if form == it["word"])
            key[it["id"]] = dict(stem_boundary=k, note="UD lemma split; a speaker may rightly cut more finely")
        key.setdefault(it["id"], {})["source"] = it.pop("source")     # the source would give the dialect away: it lives in the key only
    batch = dict(batch="b001", created=C.stamp(), tool="participation/annotate.html", items=out,
                 text_licences="UD treebanks CC BY-SA 4.0 (CAVaL CC BY-NC-SA 4.0); Wikipedia CC BY-SA; web text ODC-By; shown for annotation only",
                 note="contains no personal data about annotators; the form adds a random annotator code, nothing else")
    d = root / "annotation"
    d.mkdir(exist_ok=True)
    C.dump_json(batch, d / "batch_b001.json")
    C.dump_json(dict(batch="b001", key=key, never_share_with_annotators=True), d / "batch_b001.KEY.json")
    print(f"annotation batch b001: {sum(1 for x in out if x['task'] == 'dialect_spelling')} sentences, {sum(1 for x in out if x['task'] == 'morph')} words, "
          f"{len(qc)} QC sentences; key kept apart")
    return batch


def open_pool(root, v):
    p = pathlib.Path(root) / "pools" / f"{v}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return open(p, "w", encoding="utf-8")


def ud_test_sentences(root):
    out = []
    for sid in UD:
        try:
            out += [s["text"] for s in ud_sentences(root, sid, "test")]
        except FileNotFoundError:
            pass
    return out


def udhr_paragraphs(path):
    import xml.etree.ElementTree as ET
    r = ET.parse(path).getroot()
    ns = "{http://efele.net/udhr}"
    return [" ".join("".join(p.itertext()).split()) for tag in ("preamble", "article") for b in r.iter(ns + tag) for p in b.iter(ns + "para")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "fetch", "build"])
    ap.add_argument("--profile", default="smoke")
    ap.add_argument("--root", default="/tmp/mp_data")
    ap.add_argument("--extra", default="")
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--eastern-cap-gb", type=float, default=0)
    a = ap.parse_args()
    extra = tuple(x.strip() for x in a.extra.split(",") if x.strip())
    if a.cmd == "plan":
        print_plan(a.profile, extra)
    elif a.cmd == "fetch":
        fetch(a.profile, a.root, extra)
    else:
        build(a.profile, a.root, a.workers or None, extra, a.eastern_cap_gb or None)


if __name__ == "__main__":
    main()
