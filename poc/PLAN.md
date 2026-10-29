# Mashtots PoC: the clarified plan

Date 2026-10-28. Written after four rounds of questions with the owner, before any GPU run. This is the plan; `PREREG.md` holds the analysis rules
that are frozen (hashed) inside the notebook before any model trains; `PREDICTIONS.md` holds my forecasts, also written before any run.

## What the owner decided

| question | answer |
|---|---|
| Claims the PoC must carry | all four: the **token tax** (Measured), a **script-aware tokenizer** closes part of it, a **small Armenian-only LM** reaches a bits-per-byte floor at a budget, and the **X3D demo shows the real model** |
| Varieties | **Eastern and Western weighted equally** in every headline number; Grabar (Classical) reported on its own |
| Western parity in practice | **equal in evaluation, capped upsampling in training** (a Western byte is repeated at most 4 times); the remaining gap is the funded ask |
| Grabar | **both arms**: models with and without Classical training text, so the PoC shows what Classical text buys |
| Datasets | every candidate, plus whatever NVIDIA and Hugging Face have (checked: NVIDIA has no Armenian text data, see `DATA-CARD.md`) |
| Tokenizer x LM design | **full grid**: every tokenizer arm at every model size |
| Model sizes | **6M to 150M** non-embedding parameters, 5 sizes, the top two (85M, 150M) inside the deck's Established range (70M to 1B) |
| Budget | **about 150 compute units** on hagopjay's Colab Pro G4; units per hour not yet known, so the notebook takes `UNITS_PER_HOUR` and projects the cost from a measured throughput before training |
| Annotation first | **dialect + orthography** per sentence, and **morpheme segmentation** |
| Annotation tool | **a simple static web form** (one HTML file, no server; contributions exported as JSON) |
| Participants | Western speakers, schools, churches / Mekhitarists, scholars / linguists |
| Governance and licence of contributions | **decided later**: the consent-and-credit template leaves the licence as a blank with the options laid out |
| Audiences | an **art submission** (an X3D piece made from the real model's attention, with the other threads' visuals), cultural foundations, research grants, tech / accelerators, church / institutions |
| Deliverables | one-page summary (md), figures as PNG, a demo link (prepared, publishing needs a separate OK), budget + roadmap |

## The four claims and how each is tested

1. **Token tax (Measured).** UDHR Armenian / English token ratio for o200k, cl100k, Llama 3.x, Qwen 2.5, Gemma 3, DeepSeek V3, Mistral Tekken (= Nemotron), plus
   tokens per word on four UD treebanks (Eastern ArmTDP, Eastern BSUT, Western ArmTDP, Grabar CAVaL). CPU only.
   Already measured on this Mac by the census (`../armenian-tokenizer-census`): o200k and Tekken reproduce the deck within 1 %, the others come out 2 to 5 % higher
   than the deck under every segmentation I tried (the deck's UDHR segmentation or edition is unknown). The notebook prints both and grades ours Measured.
2. **Script-aware tokenizer.** Three arms with the same vocabulary size (32,000):
   `bytes` (UTF-8 bytes, no learning), `bpe` (byte-level BPE with the usual GPT-style pre-split: the baseline every big lab uses),
   `mashtots` (character-level BPE over the 38 Armenian letters with byte fallback, so a letter is never split into bytes, plus a morpheme pre-split learned from the
   UD lemma / form pairs). Two extra fertility-only ablations separate the two ideas (`bpe+morph`, `mashtots-nomorph`).
   Measures: tokens per word per variety, the UDHR ratio against English under our own tokenizers, morpheme-boundary F1 against lemma splits, and the first Armenian merge.
3. **Bits-per-byte floor.** A plain PyTorch decoder (RMSNorm, RoPE, SwiGLU, PyTorch SDPA attention, bf16) at 6M, 15M, 40M, 85M, 150M non-embedding parameters,
   every arm, the same number of training tokens per size (equal compute): `T = min(20 N, 1.5 B)` tokens. bpb is measured on held-out text per variety
   (Eastern: ArmWeb test_iid, UD ArmTDP and BSUT test; Western: FineWeb-2 hyw test after decontamination, UD Western test, held-out Western Wikipedia; Grabar: CAVaL test).
   A fit `bpb(N) = A N^-alpha + E` per arm is compared with the deck's `4.9e5 N^-0.795 + 0.439`, which is Established only within 70M to 1B. Points below 70M test the deck's
   curve outside its range (graded accordingly). Grabar arm: `bpe` at 15M and 40M with and without Classical text.
   Extra capability check: MultiBLiMP minimal pairs (Eastern and Western grammaticality) scored by each model.
4. **Real model in X3D.** From the largest finished `bytes` model (letter-level attention needs byte positions inside letters) and the largest `mashtots` model
   (letters are tokens, so they have their own input embeddings): 36 x 36 letter-to-letter attention per layer and head, the three most structured heads (selection rule in
   `PREREG.md`), letter embeddings (input and contextual, 3-D PCA), and per-glyph attention and surprisal for the landing's two texts (Proverbs 1:2 and the Lord's Prayer, Grabar).
   One JSON file, schema in `EXPORT-SCHEMA.md`. The art piece itself is a new scene built after the G4 run; `../mashtots-landing/` is read only.

## Data (details, licences and sizes in `DATA-CARD.md`)

* **Eastern:** ArmWeb (COPA-AI, ODC-By; decontaminated, with held-out splits), Armenian Wikipedia, public-domain Eastern literature, UD Eastern train splits;
  FineWeb-2 `hye` only in `full` and only after our own decontamination (COPA measured 17 % benchmark overlap, and its train split overlaps its own test split).
* **Western:** FineWeb-2 `hyw`, GlotCC `hyw`, Western Wikipedia, UD Western train split. All of it is labelled by language-ID tools that can confuse Western with Eastern
  in classical spelling; every document is re-labelled by our variety classifier, and the agreement is reported.
* **Grabar:** UD CAVaL train split (CC BY-NC-SA: the `+Grabar` models carry a non-commercial condition), Armenian Wikisource documents the classifier labels Grabar.
* **Cleaning:** NFC, Armenian-letter share, length, exact deduplication, and 13-word-gram decontamination against every evaluation text (including the probe texts).
* **The dialect / orthography confound.** UD Western is in classical spelling and UD Eastern in reformed spelling, so a classifier trained on them can learn spelling,
  not dialect (Iranian Armenians write Eastern in classical spelling). The notebook reports a dialect x orthography cross-table; the first annotation task exists to break
  this confound with human labels.

## Run profiles (G4: RTX PRO 6000 Blackwell, 96 GB, 48 CPUs)

| profile | data download | models | purpose | projected wall time |
|---|---|---|---|---|
| `smoke` | 0.11 GB (UD, Western Wikipedia, MultiBLiMP, ArmWeb validation and test splits, FineWeb-2 Western test) | 3 arms x 6M, 20M tokens each | does everything run on the G4; measures throughput per arm | 10 to 15 min |
| `core` | 2.69 GB | 3 arms x {6M, 15M, 40M} + Grabar ablation (bpe at 15M, 40M) | tokenizer verdict, first scaling points, first real export | about 2 to 3 h (printed after the smoke's throughput) |
| `full` | 6.44 GB (+ optional HPLT / CulturaX / GlotCC Eastern) | adds 85M and 150M for all 3 arms | the scaling fit inside the deck's range | about 10 to 14 h if all 3 arms are run at 150M; `ARMS_OVERRIDE` limits it |

Wall times are estimates (Estimate) until the smoke run measures tokens per second. Cell 12 prints `hours x UNITS_PER_HOUR` for the chosen profile before anything trains,
and `MAX_HOURS` stops the training cell before a run that would cross it. Every run is resume-safe, checkpoints to Drive, and is skipped when already finished,
so `full` can be spread over several sessions. If 150 units do not cover the full grid, the order of cuts is: the 150M `bytes` run, then the 150M `mashtots` run
(the scaling fit then rests on `bpe` at 150M).

## Who runs what

| where | who | what |
|---|---|---|
| this Mac (8 GB M3) | Claude | builds the notebook; dry-runs every cell with UD text from the census folder and a tiny model (no downloads) |
| Colab Pro, G4 | **hagopjay** | runs the notebook: `smoke` first, then `core`, then `full` if the budget allows |
| `My Drive/x3d.io/mashtots-poc-runs/<run>-<profile>/` | both | results (small files, checkpoints of finished models, figures, the export JSON); shared with hagsmac37 as before |

## Hard rules the build follows

* Nothing is downloaded until the owner ticks `I_APPROVE_DOWNLOADS` in the notebook after reading the file list the notebook prints (names, sources, licences, sizes).
* No uploads or publishing from this Mac. The demo link is prepared, not published.
* No personal data from contributors in any dataset (the form collects none; the credit name is kept apart from the data).
* `../mashtots-slide1-FROZEN/` and the approved files of `../mashtots-landing/` are never edited.
* Every number in the outputs carries a grade: **Measured** (computed in this run), **Established** (published, inside its range), **Estimate** (extrapolated or projected),
  **Conjecture** (a claim of meaning). Synthetic or local dry-run numbers are labelled `DRY RUN` and never reach a funder document.
