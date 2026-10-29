#!/usr/bin/env python3
"""Shared constants for the Mashtots PoC: the alphabet, the deck's graded figures, model sizes, profiles, small IO helpers.

Every other module imports this one; it has no third-party dependencies.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import time

VERSION = "mashtots-poc v1"
LOCAL = os.environ.get("MP_LOCAL") == "1"

# ---------------------------------------------------------------- the alphabet
# Mashtots' 36 letters in alphabet order (upper case), as in ../mashtots-landing/reveal_data.py, and the two letters added in the Middle Ages.
MASHTOTS_36 = "ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓՔ"
LATER_2 = "ՕՖ"
LETTERS_38 = MASHTOTS_36 + LATER_2
LOWER = {c: chr(ord(c) + 48) for c in LETTERS_38}          # U+0531..0556 -> U+0561..0586
LETTERS_38_LOWER = "".join(LOWER[c] for c in LETTERS_38)
ECH_YIWN = "և"                                          # և, a ligature in classical spelling, a letter in the reformed one
ARMENIAN_LETTERS = set(LETTERS_38 + LETTERS_38_LOWER + ECH_YIWN)
# letters as numbers: 1..9, 10..90, 100..900, 1000..9000 in alphabet order
NUMERAL = {c: (i % 9 + 1) * 10 ** (i // 9) for i, c in enumerate(MASHTOTS_36)}

# The landing's two texts exactly as its glyph atlas writes them (upper case, the comma as the only punctuation; make_landing.py: slots and PRAYER).
# The models read the lower-case form with a capital first letter; character i of the probe is glyph i of the landing (spaces included).
LANDING_TEXTS = {
    "proverbs_1_2": "ՃԱՆԱՉԵԼ ԶԻՄԱՍՏՈՒԹԻՒՆ ԵՒ ԶԽՐԱՏ, ԻՄԱՆԱԼ ԶԲԱՆՍ ՀԱՆՃԱՐՈՅ",
    "lords_prayer": ("ՀԱՅՐ ՄԵՐ, ՈՐ ՅԵՐԿԻՆՍ ԵՍ, ՍՈՒՐԲ ԵՂԻՑԻ ԱՆՈՒՆ ՔՈ, ԵԿԵՍՑԷ ԱՐՔԱՅՈՒԹԻՒՆ ՔՈ, ԵՂԻՑԻՆ ԿԱՄՔ ՔՈ, ՈՐՊԷՍ ՅԵՐԿԻՆՍ ԵՒ ՅԵՐԿՐԻ, "
                     "ԵՒ ԹՈՂ ՄԵԶ ԶՊԱՐՏԻՍ ՄԵՐ, ՈՐՊԷՍ ԵՒ ՄԵՔ ԹՈՂՈՒՄՔ ՄԵՐՈՑ ՊԱՐՏԱՊԱՆԱՑ, ԵՒ ՄԻ ՏԱՆԻՐ ԶՄԵԶ Ի ՓՈՐՁՈՒԹԻՒՆ, ԱՄԷՆ,"),
}


def probe_text(upper):
    low = "".join(LOWER.get(c, c) for c in upper)
    return low[:1].upper() + low[1:] if low else low


PROBES = {k: probe_text(v) for k, v in LANDING_TEXTS.items()}

# ---------------------------------------------------------------- the deck's figures, with the deck's grades
DECK = {
    "token_bill_udhr_hy_over_en": {"grade": "Measured (deck)", "values": {
        "o200k": 1.51, "tekken": 1.74, "gemma": 2.67, "deepseek_v3": 2.87, "qwen2.5": 5.41, "llama3": 8.73, "cl100k": 10.15}},
    "word_shapes": {"grade": "Measured (deck)", "word_forms_hy_en": [19910, 10311], "tokens_per_word_en_hy": [1.82, 2.64]},
    "data_law": {"grade": "Established (published fit); its plotted points are placeholders", "L(D)": "1.69 + 410.7 D^-0.28"},
    "armenian_floor": {"grade": "Established within 70M-1B parameters, Estimate beyond", "A": 4.9e5, "alpha": 0.795, "E": 0.439,
                       "range": [70e6, 1e9]},
    "closing": {"grade": "Conjecture", "text": "a sacred language can become a domain programming language"},
}


def deck_floor(n_params):
    f = DECK["armenian_floor"]
    return f["A"] * n_params ** -f["alpha"] + f["E"]


def floor_grade(n_params):
    lo, hi = DECK["armenian_floor"]["range"]
    return "Established" if lo <= n_params <= hi else "Estimate (outside 70M-1B)"


# external reference point (published): COPA-AI ArmWeb card / arXiv 2609.03350, 410M-parameter ablations, panel-mean bpb
COPA_REFERENCE = {"params": 410e6, "bpb_panel_mean_union": 0.532, "bpb_best_single": 0.545, "grade": "Established (published, different eval panel)"}

# ---------------------------------------------------------------- tokenizer arms and model sizes
ARMS = ["bytes", "bpe", "mashtots"]
VOCAB = 32000
# d_model, layers, heads -> non-embedding params about 12 * L * d^2 (SwiGLU hidden = 8/3 d)
SIZES = {
    "6M": dict(d=256, L=8, H=4),
    "15M": dict(d=384, L=8, H=6),
    "40M": dict(d=512, L=12, H=8),
    "85M": dict(d=768, L=12, H=12),
    "150M": dict(d=896, L=16, H=14),
    "tiny": dict(d=48, L=2, H=2),            # local dry run only
}
SEQ_LEN = 1024
TOKENS_PER_PARAM, TOKEN_CAP = 20, 1.5e9

PROFILES = {
    "smoke": dict(sizes=["6M"], arms=ARMS, tokens_override=20e6, grabar_sizes=[], sources_tier=0),
    "core": dict(sizes=["6M", "15M", "40M"], arms=ARMS, tokens_override=None, grabar_sizes=["15M", "40M"], sources_tier=1),
    "full": dict(sizes=["6M", "15M", "40M", "85M", "150M"], arms=ARMS, tokens_override=None, grabar_sizes=["15M", "40M"], sources_tier=2),
}
LOCAL_PROFILE = dict(sizes=["tiny"], arms=ARMS, tokens_override=60_000, grabar_sizes=["tiny"], sources_tier=0)

GRADES = ("Measured", "Established", "Estimate", "Conjecture")


def non_embedding_params(size):
    s = SIZES[size]
    d, L = s["d"], s["L"]
    hidden = swiglu_hidden(d)
    return L * (4 * d * d + 3 * d * hidden + 2 * d) + d


def swiglu_hidden(d):
    return int(math.ceil(8 * d / 3 / 64) * 64)


def train_tokens(size, profile_cfg):
    if profile_cfg.get("tokens_override"):
        return int(profile_cfg["tokens_override"])
    return int(min(TOKENS_PER_PARAM * non_embedding_params(size), TOKEN_CAP))


def run_id(arm, size, grabar=False):
    return f"{arm}-{size}" + ("-G" if grabar else "")


# ---------------------------------------------------------------- small helpers
def sha256_file(path, n=None):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n] if n else h.hexdigest()


def dump_json(obj, path):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    tmp.replace(path)
    return path


def load_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except FileNotFoundError:
        return default


def stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def is_armenian_char(ch):
    return "Ա" <= ch <= "֏" or "ﬓ" <= ch <= "ﬗ"


def armenian_share(text):
    """Share of letters (any script) that are Armenian."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if is_armenian_char(c)) / len(letters)
