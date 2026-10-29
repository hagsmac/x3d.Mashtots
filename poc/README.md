# Mashtots PoC

Proof of concept for Mashtots System 2: the token tax Armenian pays, a script-aware tokenizer, small Armenian-only PyTorch models scaled against the deck's floor,
and the real model exported for the X3D demo. Built 2026-10-28/29 by Claude; run by the owner on hagopjay's Colab Pro G4.

| file | what |
|---|---|
| `PLAN.md` | the clarified plan (the owner's answers, design, profiles, budget) |
| `RUNBOOK.md` | what to press, what to expect, what to do when it breaks |
| `PREREG.md` | analysis rules, frozen by hash in the notebook before training |
| `PREDICTIONS.md` | my forecasts, written before any run, to be Brier-scored |
| `DATA-CARD.md` | every source: licence, size, revision, role, known limits |
| `EXPORT-SCHEMA.md` | the JSON the X3D scene can load |
| `FUNDING-ONEPAGER.md` | the graded one-pager, budget and roadmap |
| `participation/` | `annotate.html` (offline form), `TASKS.md`, `CONSENT-AND-CREDIT.md`, `GOVERNANCE.md` |
| `mashtots_poc.ipynb` | the notebook (self-contained) |
| `build_notebook.py`, `run_notebook_local.py` | build it; dry-run it on the Mac |
| `mp_*.py`, `nb_helpers.py` | data, tokenizers, model, trainer, scoring, analysis, export, notebook glue |
| `examples/` | dry-run outputs (tiny model; numbers meaningless) |

Rebuild and test: `python3 -I build_notebook.py && python3 run_notebook_local.py mashtots_poc.ipynb` (about one minute; needs `../armenian-tokenizer-census/data`).
