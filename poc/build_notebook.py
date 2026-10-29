#!/usr/bin/env python3
"""Assemble mashtots_poc.ipynb: one self-contained Colab notebook (all code, PREREG.md and the UDHR texts embedded, gzip + base64).

usage: python3 -I build_notebook.py [OUT.ipynb]
The same notebook dry-runs on a Mac with run_notebook_local.py (MP_LOCAL=1: no downloads, UD text from the census folder, a tiny model).
"""
import base64
import gzip
import hashlib
import json
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = "v1"
FILES = ["mp_common.py", "mp_data.py", "mp_tok.py", "mp_model.py", "mp_train.py", "mp_eval.py", "mp_analyze.py", "mp_export.py", "nb_helpers.py", "PREREG.md"]
UDHR = os.environ.get("MP_UDHR_SRC", os.path.expanduser("~/Projects/x3d/work/armenian-tokenizer-census/data/udhr"))
EMBED = [(f, os.path.join(HERE, f)) for f in FILES] + [(f"udhr/{n}", os.path.join(UDHR, n)) for n in ("udhr_hye.xml", "udhr_eng.xml")]
BUILD_HASH = hashlib.sha256(b"".join(open(p, "rb").read() for _, p in EMBED)).hexdigest()[:8]

cells = []


def md(src):
    cells.append(("markdown", textwrap.dedent(src).strip("\n"), {}))


def code(src, form=False):
    cells.append(("code", textwrap.dedent(src).strip("\n"), {"cellView": "form"} if form else {}))


md(f'''
# Mashtots System 2, proof of concept: what Armenian costs a language model, and what an Armenian-aware model gets back  (build {BUILD}, `{BUILD_HASH}`)

**What this notebook does**, top to bottom, each step graded (**Measured / Established / Estimate / Conjecture**):
1. **The token bill.** How many more tokens the big tokenizers spend on the UDHR in Armenian than in English, and per word in Eastern, Western and Grabar.
2. **A script-aware tokenizer.** Byte-level BPE (what the big labs do) against a *Mashtots* tokenizer (the 38 letters are atoms, words are cut at their endings),
   trained on Eastern and Western text in equal parts.
3. **Small Armenian-only models** in plain PyTorch, every tokenizer at every size, bits per byte on held-out Eastern, Western and Grabar text,
   and the scaling curve against the deck's `bpb(N) = 4.9e5 N^-0.795 + 0.439`.
4. **The real model for the X3D demo**: letter-to-letter attention, letter embeddings and the landing's two texts, as one JSON.

The rules are **pre-registered** (`PREREG.md`, hashed in the Freeze cell before any model trains); my forecasts are in `PREDICTIONS.md`.

**How to run it.**
1. Runtime ▸ Change runtime type ▸ **G4 GPU**. Sign in as **hagopjay** (the account with the G4).
2. Shift+Enter on each cell, top to bottom, with `PROFILE = "smoke"` first (10 to 15 minutes, about 0.1 GB of downloads).
3. Cell 7 prints every file that will be downloaded, with its licence and size. **Nothing is downloaded until you tick `I_APPROVE_DOWNLOADS` in cell 2** and run cell 8.
4. Cell 12 measures the speed of this GPU and prints what the chosen profile will cost in hours (and in compute units if you fill in `UNITS_PER_HOUR`).
   Read it before cell 13 trains anything. `MAX_HOURS` stops training cleanly at a checkpoint; running cell 13 again continues.
5. If a cell prints ❌ or a traceback, stop and send Claude what it said.

**Where results go.** `My Drive/x3d.io/mashtots-poc-runs/<RUN_NAME>-<PROFILE>/` (small files, finished models, figures, the export JSON), inside the folder
already shared with hagsmac37. **When you are done: Runtime ▸ Disconnect and delete runtime** (an idle G4 still spends units).
''')

code('''
# 1. What machine did we get?
import shutil, subprocess
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout if shutil.which("nvidia-smi") else
      "No GPU found. In Colab: Runtime > Change runtime type > G4 GPU, then run this cell again.")
''')

code(f'''
#@title 2. Configuration {{ display-mode: "form" }}
PROFILE = "smoke"  #@param ["smoke", "core", "full"]
RUN_NAME = "run1"  #@param {{type:"string"}}
I_APPROVE_DOWNLOADS = False  #@param {{type:"boolean"}}
UNITS_PER_HOUR = 0.0  #@param {{type:"number"}}
MAX_HOURS = 0.0  #@param {{type:"number"}}
ARMS_OVERRIDE = ""  #@param {{type:"string"}}
SIZES_OVERRIDE = ""  #@param {{type:"string"}}
EXTRA_SOURCES = ""  #@param {{type:"string"}}
ALLOW_MIRRORS = True  #@param {{type:"boolean"}}
COMPILE = True  #@param {{type:"boolean"}}
DRIVE_BASE = "x3d.io/mashtots-poc-runs"  #@param {{type:"string"}}
BUILD, BUILD_HASH = "{BUILD}", "{BUILD_HASH}"
import os, sys, json, time, pathlib
IN_COLAB = "google.colab" in sys.modules
LOCAL = os.environ.get("MP_LOCAL") == "1"
ROOT = pathlib.Path("/content/mp") if IN_COLAB else pathlib.Path(os.environ.get("MP_ROOT", "/tmp/mp_nb"))
SRC, DATA = ROOT / "src", ROOT / ("local" if LOCAL else PROFILE)
RUNS, RESULTS = DATA / "runs", DATA / "results"
for _d in (SRC, DATA, RUNS, RESULTS):
    _d.mkdir(parents=True, exist_ok=True)
EXTRA = tuple(x.strip() for x in EXTRA_SOURCES.split(",") if x.strip())     # optional sources: hplt, culturax, glotcc_hye
WORKERS = max(1, min(46, (os.cpu_count() or 2) - 2)) if not LOCAL else 2
if IN_COLAB:
    try:
        from google.colab import userdata                                         # a Hugging Face token in Colab's Secrets (key icon), if you added one
        os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN") or ""
    except Exception:
        pass
print(f"build {{BUILD}} {{BUILD_HASH}} | profile {{PROFILE}} | run {{RUN_NAME}} | downloads approved: {{I_APPROVE_DOWNLOADS}} | workers {{WORKERS}} | data {{DATA}}")
''', form=True)

code('''
# 3. Google Drive for results. A pop-up asks for access: choose the account that owns this runtime (hagopjay).
DRIVE_OUT = DRIVE_RUNS = None
if IN_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")
    DRIVE_OUT = f"/content/drive/MyDrive/{DRIVE_BASE}/{RUN_NAME}-{PROFILE}"
    DRIVE_RUNS = f"{DRIVE_OUT}/runs"
    os.makedirs(DRIVE_RUNS, exist_ok=True)
print("results folder:", DRIVE_OUT)
''')

SRC_CELL = '''
#@title 4. Write the source files (code, PREREG.md and the UDHR texts are embedded in this notebook; hashes below) { display-mode: "form" }
import base64, gzip, hashlib
_FILES = {
%s
}
for _n, _b in _FILES.items():
    _p = (DATA / _n) if _n.startswith("udhr/") else (SRC / _n)
    _p.parent.mkdir(parents=True, exist_ok=True)
    _p.write_bytes(gzip.decompress(base64.b64decode("".join(_b))))
sys.path.insert(0, str(SRC))
import nb_helpers as H
print("wrote", len(_FILES), "files; sha256 prefixes:")
for _n in sorted(_FILES):
    _p = (DATA / _n) if _n.startswith("udhr/") else (SRC / _n)
    print(" ", hashlib.sha256(_p.read_bytes()).hexdigest()[:12], _n)
'''
entries = []
for name, path in EMBED:
    b64 = base64.b64encode(gzip.compress(open(path, "rb").read(), mtime=0)).decode()
    wrapped = "\n".join(f"        {chunk!r}," for chunk in textwrap.wrap(b64, 100))
    entries.append(f"    {name!r}: [\n{wrapped}\n    ],")
code(SRC_CELL % "\n".join(entries), form=True)

code('''
# 5. Install what is missing (tokenizers, tiktoken, pyarrow, ...; torch is Colab's own and is not touched), then report versions
H.install()
H.env_report()
''')

code('''
# 6. Doctor: GPU, the model code, the tokenizers, the network, disk and Drive. Continue only if the last line says ALL GOOD.
import mp_data as D
_rows, _total = D.plan(PROFILE if not LOCAL else "local", EXTRA)
OK = H.doctor(SRC, DATA, DRIVE_OUT, need_gb=max(2.0, 5 * _total / 1e9))
''')

code('''
# 7. What would be downloaded for this profile: names, sources, licences, sizes (DATA-CARD.md has the details). Nothing is fetched here.
_rows, _total = D.print_plan(PROFILE if not LOCAL else "local", EXTRA)
print("\\nNVIDIA: no Armenian text data exists in the Nemotron datasets (checked 2026-10-28); Nemotron is measured through its tokenizer only.")
print("To go on, tick I_APPROVE_DOWNLOADS in cell 2, run cell 2 again, then cell 8." if not I_APPROVE_DOWNLOADS else "Downloads approved in cell 2.")
''')

code('''
# 8. Fetch (resume-safe), then build: evaluation sets first, then cleaned, decontaminated, deduplicated training pools (Eastern / Western / Grabar)
if LOCAL:
    print("local dry run: no downloads; UD text from", os.environ.get("MP_UD_DIR"))
else:
    assert I_APPROVE_DOWNLOADS, "tick I_APPROVE_DOWNLOADS in cell 2 after reading the list in cell 7"
    H.sh([sys.executable, str(SRC / "mp_data.py"), "fetch", "--profile", PROFILE, "--root", str(DATA), "--extra", ",".join(EXTRA)])
if not (DATA / "data_stats.json").exists():
    H.sh([sys.executable, str(SRC / "mp_data.py"), "build", "--profile", PROFILE if not LOCAL else "local", "--root", str(DATA),
          "--workers", str(WORKERS), "--extra", ",".join(EXTRA)])
_ds = json.loads((DATA / "data_stats.json").read_text())
print("classifier (single UD test sentences):", _ds["classifier"]["accuracy"])
print("pools MB:", {k: round(v["bytes"] / 1e6, 1) for k, v in _ds["pools"].items()})
print("dialect x spelling (MB):", {k: round(v / 1e6, 1) for k, v in _ds.get("crosstab_bytes", {}).items()})
H.checkpoint(DATA, DRIVE_OUT, ["data_stats.json", "fetch_log.json", "annotation"])   # annotation/: the first batch for participation/annotate.html (its KEY file stays with the coordinator)
''')

code('''
# 9. The token bill: eight big-lab tokenizers on the UDHR (Armenian / English) and on four treebanks. CPU only.
#    Gemma and Llama are gated: with ALLOW_MIRRORS a public copy is used only if it is byte-identical (sha256) to the official file.
H.sh([sys.executable, str(SRC / "mp_tok.py"), "bill", "--root", str(DATA), "--out", str(RESULTS)] + (["--allow-mirrors"] if ALLOW_MIRRORS else []))
H.checkpoint(DATA, DRIVE_OUT, ["results"])
''')

code('''
# 10. Our tokenizers: learn the suffix inventory from the UD lemmas, train bpe / mashtots / two ablations on an equal Eastern-Western sample,
#     measure them, then encode the training pools for the trainer (resume-safe).
if not (DATA / "tokenizers" / "train_report.json").exists():
    H.sh([sys.executable, str(SRC / "mp_tok.py"), "train", "--root", str(DATA), "--sample-mb", "300"])
H.sh([sys.executable, str(SRC / "mp_tok.py"), "fertility", "--root", str(DATA), "--out", str(RESULTS)])
H.sh([sys.executable, str(SRC / "mp_tok.py"), "encode", "--root", str(DATA), "--workers", str(WORKERS)])
H.checkpoint(DATA, DRIVE_OUT, ["tokenizers", "results", "tokens/encode_report.json"])
''')

code('''
# 11. FREEZE the pre-registration and the code before any model trains (sha256 of PREREG.md and every code file)
FROZEN = H.freeze(SRC, DATA, PROFILE, dict(build=BUILD, build_hash=BUILD_HASH, run=RUN_NAME))
H.checkpoint(DATA, DRIVE_OUT, ["PREREG.md", "PREREG.sha256"])
''')

code('''
# 12. What will training cost? Measures this GPU's speed for every (tokenizer, size) of the profile (a few minutes), then projects the hours.
SPECS = H.grid(PROFILE, ARMS_OVERRIDE, SIZES_OVERRIDE)
BENCH = H.bench(SRC, DATA, SPECS, compile_=COMPILE)
PLAN_ROWS, PLAN_HOURS = H.project(SPECS, BENCH, UNITS_PER_HOUR)
H.checkpoint(DATA, DRIVE_OUT, ["bench"])
''')

code('''
# 13. Train the grid, smallest first (resume-safe; each run checkpoints to Drive every 15 minutes and is skipped once finished).
assert (DATA / "PREREG.sha256").exists(), "run the Freeze cell first"
DONE, LEFT = H.train_grid(SRC, DATA, SPECS, RUNS, DRIVE_RUNS, max_hours=MAX_HOURS, compile_=COMPILE)
''')

code('''
# 14. Analyze exactly as pre-registered; the verdicts, the tables and the figures
H.sh([sys.executable, str(SRC / "mp_analyze.py"), "--root", str(DATA), "--runs", str(RUNS), "--out", str(RESULTS)])
H.show(sorted((RESULTS / "figs").glob("*.png")))
H.checkpoint(DATA, DRIVE_OUT, ["results"])
''')

code('''
# 15. Export the real model for the X3D scene: letter attention (36 x 36 per layer and head), letter embeddings, the landing's two texts
H.sh([sys.executable, str(SRC / "mp_export.py"), "--root", str(DATA), "--runs", str(RUNS), "--out", str(RESULTS / "mashtots_model_export.json"),
      "--device", "cpu" if LOCAL else "cuda"])
H.show([RESULTS / "figs" / "export_preview.png"])
H.checkpoint(DATA, DRIVE_OUT, ["results"])
''')

code('''
# 16. Package: run record and a last copy of everything small to Drive
import platform, importlib.metadata as _md
_info = dict(build=BUILD, build_hash=BUILD_HASH, profile=PROFILE, run=RUN_NAME, finished=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
             python=platform.python_version(), packages={m: _md.version(m) for m in ("torch", "tokenizers", "tiktoken", "pyarrow", "huggingface_hub")},
             runs_done=sorted(p.parent.name for p in RUNS.glob("*/done.json")), projected_hours=round(PLAN_HOURS, 2), units_per_hour=UNITS_PER_HOUR)
(DATA / "run_info.json").write_text(json.dumps(_info, indent=1))
H.checkpoint(DATA, DRIVE_OUT, ["run_info.json", "results", "data_stats.json", "PREREG.md", "PREREG.sha256", "tokenizers"])
print("DONE. Results are in", DRIVE_OUT)
print("Tell Claude the results are in Drive. If you are finished: Runtime > Disconnect and delete runtime (an idle G4 still spends units).")
''')


def to_ipynb(path):
    nb_cells = []
    for i, (kind, src, meta) in enumerate(cells):
        cid = hashlib.sha1(f"{i}:{src[:60]}".encode()).hexdigest()[:8]
        lines = src.split("\n")
        c = {"cell_type": kind, "id": cid, "metadata": dict(meta), "source": [ln + "\n" for ln in lines[:-1]] + [lines[-1]]}
        if kind == "code":
            c["outputs"], c["execution_count"] = [], None
        nb_cells.append(c)
    nb = {"nbformat": 4, "nbformat_minor": 5, "cells": nb_cells,
          "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "G4"},
                       "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}}}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(nb, fh, indent=1)
    return path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "mashtots_poc.ipynb")
    to_ipynb(out)
    print("wrote", out, os.path.getsize(out), "bytes,", len(cells), "cells, build", BUILD, BUILD_HASH)
