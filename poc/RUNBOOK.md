# Mashtots PoC: runbook (read before pressing anything)

Notebook: `mashtots_poc.ipynb` (built by `python3 -I build_notebook.py`; the build hash is in its title and cell 2). Run it on **hagopjay's Colab Pro, G4 runtime**.

## First time: the smoke run (10 to 15 minutes, 0.11 GB of downloads)

1. Upload `mashtots_poc.ipynb` to Colab (File ▸ Upload notebook), Runtime ▸ Change runtime type ▸ **G4**.
2. Run cells 1 to 7. Cell 6 must end with **ALL GOOD**. Read the download list in cell 7.
3. If the list is fine: tick **`I_APPROVE_DOWNLOADS`** in cell 2, run cell 2 again, then cells 8 to 16.
4. Tell Claude when cell 16 says DONE. Then Runtime ▸ **Disconnect and delete runtime**.

Optional before the bill (cell 9): to use the official Gemma 3 and Llama 3.2 tokenizers, accept their licences on Hugging Face as hagopjay and add a token named `HF_TOKEN` in
Colab's Secrets (key icon). Without it, `ALLOW_MIRRORS` uses public copies only when they are byte-identical to the official files.

## Then: core (about 2 to 3 hours, 2.7 GB), and full only if the budget allows

Set `PROFILE = "core"`, fill in **`UNITS_PER_HOUR`** (Colab shows it under Runtime ▸ Change runtime type / Resources), run from cell 2 down.
**Cell 12 prints the projected hours and units before anything trains**: stop there if it is too much. `MAX_HOURS` stops cell 13 cleanly at a checkpoint.
For `full`, `ARMS_OVERRIDE = "bpe,mashtots"` or `SIZES_OVERRIDE = "85M,150M"` shrink the grid.

## The cells

| # | cell | what you should see |
|---|---|---|
| 1 | Machine | the GPU table (RTX PRO 6000 Blackwell) |
| 2 | Configuration | `build v1 <hash> \| profile smoke \| ... downloads approved: False` |
| 3 | Drive | a Google pop-up: allow, as hagopjay |
| 4 | Source files | 12 file names with hashes |
| 5 | Setup | package versions and the GPU |
| 6 | **Doctor** | five or six ✅ and **ALL GOOD**. Any ❌: stop and send the line to Claude |
| 7 | Download list | every file with licence and size; nothing fetched |
| 8 | Data | fetch, then pools in MB, classifier accuracy, dialect x spelling table, the annotation batch |
| 9 | Token bill | eight tokenizers, ours vs the deck's ratio |
| 10 | Our tokenizers | suffix inventory, four trained tokenizers, tokens per word, round-trip failures **0** |
| 11 | **Freeze** | `FROZEN` and the hashes: the rules are locked before training |
| 12 | Cost | throughput per model, projected hours (and units) |
| 13 | Train | per run: loss, tokens/s, ETA; `done <run>: bpb ...` |
| 14 | Analyze | `RESULTS.md` (verdicts H1-H6) and the figures |
| 15 | Export | `mashtots_model_export.json` and a preview figure |
| 16 | Package | `DONE. Results are in ...` |

Every cell can be run again. After a disconnect, run from cell 2 down: the data is rebuilt (minutes), finished runs are skipped, an unfinished one resumes from its
Drive checkpoint.

## If something goes wrong

| symptom | likely cause | what to do |
|---|---|---|
| no GPU in cell 1 | wrong runtime | Runtime ▸ Change runtime type ▸ G4, then cell 1 again |
| ❌ network in cell 6 | Hugging Face or GitHub down | wait and rerun cell 6 |
| cell 8 stops with `tick I_APPROVE_DOWNLOADS` | as designed | read cell 7, tick, rerun cell 2 then 8 |
| a bill row "skipped" | gated tokenizer without token, mirror differs | fine; the row says why |
| `round-trip failures` above 0 in cell 10 | a tokenizer loses bytes | stop; send Claude the line |
| `non-finite loss` | instability | send Claude the run name and the last lines |
| `MAX_HOURS reached` | as designed | rerun cell 13 (raise MAX_HOURS) to continue |
| a prompt to buy compute | Colab | decline; Claude never buys anything |
