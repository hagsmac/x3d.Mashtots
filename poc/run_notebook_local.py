#!/usr/bin/env python3
"""Dry-run the notebook's code cells on this Mac: MP_LOCAL=1, no Drive, no pip, no downloads, UD text from the census folder, a tiny model on the CPU.

usage: python3 run_notebook_local.py [mashtots_poc.ipynb]
Executes the notebook's own code cells (built by build_notebook.py) in order in one namespace and stops at the first exception.
Plumbing only: the numbers are labelled DRY RUN.
"""
import json
import os
import sys
import time
import traceback

CENSUS = os.path.expanduser("~/Projects/x3d/work/armenian-tokenizer-census/data")
nb = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "mashtots_poc.ipynb"))
os.environ.update(MP_LOCAL="1", MP_ROOT=os.environ.get("MP_ROOT", "/tmp/mp_nb_dry"), MP_UD_DIR=CENSUS, MP_CENSUS_DIR=CENSUS,
                  TIKTOKEN_CACHE_DIR=os.path.join(CENSUS, "tiktoken"))
ns = {"__name__": "__main__"}
t_all = time.time()
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] != "code":
        continue
    src = "".join(c["source"])
    print(f"\n=== cell {i}: {src.splitlines()[0][:90]}", flush=True)
    t0 = time.time()
    try:
        exec(compile(src, f"<cell {i}>", "exec"), ns)
    except Exception:
        traceback.print_exc()
        print(f"!!! cell {i} failed after {time.time() - t0:.1f}s")
        sys.exit(1)
    print(f"--- cell {i} ok ({time.time() - t0:.1f}s)", flush=True)
print(f"\nDRY RUN COMPLETE in {time.time() - t_all:.0f} s")
