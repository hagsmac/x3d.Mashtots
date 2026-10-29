# Data card: Mashtots PoC

Checked on 2026-10-28 from the Hugging Face and GitHub APIs (metadata only; nothing downloaded to this Mac). Each source is pinned to a revision in
`mp_data.py` (`SOURCES`), so a run fetches exactly the files listed here. Counts after cleaning are written by the notebook to `data_stats.json` (Measured, per run).

## Sources

Tier: **0** = smoke, **1** = core, **2** = full, **opt** = only with `EXTRA_SOURCES`. Size = download size of the files used.

| id | what | variety | licence | size | tier | used for |
|---|---|---|---|---|---|---|
| `ud_armtdp` | UD Armenian ArmTDP r2.18 | Eastern | CC BY-SA 4.0 | 14 MB | 0 | train split, test split for scoring, classifier, morpheme gold |
| `ud_bsut` | UD Armenian BSUT r2.18 | Eastern | CC BY-SA 4.0 | 6 MB | 0 | train, test, classifier |
| `ud_hyw` | UD Western Armenian ArmTDP r2.18 | Western | CC BY-SA 4.0 | 16 MB | 0 | train, test, classifier, morpheme gold |
| `ud_caval` | UD Classical Armenian CAVaL r2.18 (the **Grabar Gospels**) | Grabar | **CC BY-NC-SA 4.0** | 13 MB | 0 | Grabar train split (`-G` runs only), test, classifier |
| `udhr` | UDHR Armenian + English (eric-muller/udhr XML), **embedded in the notebook** | Eastern | UN text, free to reproduce | 44 KB | 0 | token bill only; excluded from training |
| `armweb_val` | ArmWeb validation split (COPA-AI) | Eastern | ODC-By 1.0 | 15 MB | 0 only | the smoke run's Eastern training text |
| `armweb_test` | ArmWeb test_iid | Eastern | ODC-By 1.0 | 15 MB | 0 | Eastern scoring (news), the deck comparison set |
| `wiki_hyw` | Western Armenian Wikipedia 20231101.hyw | Western | CC BY-SA 3.0 / GFDL | 27 MB | 0 | Western training; 2 % of articles held out for scoring |
| `fw2_hyw_test` | FineWeb-2 hyw_Armn test | Western (GlotLID) | ODC-By 1.0 + Common Crawl terms | 2.5 MB | 0 | Western scoring (only documents our classifier calls Western) |
| `multiblimp` | MultiBLiMP hye + hyw | E + W | CC BY 4.0 | 5 MB | 0 | grammaticality pairs, scoring only |
| `armweb` | ArmWeb train, parts 0-4 (core) / 0-8 (full) | Eastern (+ some Western) | ODC-By 1.0 | 1.73 / 3.06 GB | 1 / 2 | the main Eastern training text: news 2011-2026, deduplicated and decontaminated by COPA-AI |
| `wiki_hy` | Armenian Wikipedia 20231101.hy | Eastern | CC BY-SA 3.0 / GFDL | 490 MB | 1 | Eastern training |
| `pd_lit` | catherinearnett/classical_armenian_pd | Eastern (literary) | CC0 1.0 | 25 MB | 1 | Eastern training; **mislabelled on HF as "classical": it is 102 public-domain 19th-20th c. Eastern works from the EANC library (Abovian, Charents, Muratsan, Nar-Dos ...)** |
| `wikisource_hy` | Armenian Wikisource 20231201.hy | mixed | CC BY-SA 3.0 / GFDL (texts mostly public domain) | 19 MB | 1 | routed by the classifier; its Grabar documents feed the `-G` runs |
| `fw2_hyw` | FineWeb-2 hyw_Armn train | Western (GlotLID) | ODC-By 1.0 + Common Crawl terms | 265 MB | 1 | the main Western training text, re-labelled by our classifier |
| `glotcc_hyw` | GlotCC-V1 hyw-Armn | Western (GlotLID) | CC0 1.0 + Common Crawl terms | 44 MB | 1 | Western training, re-labelled |
| `fw2_hye_test` | FineWeb-2 hye_Armn test | Eastern | ODC-By 1.0 + Common Crawl terms | 23 MB | 1 | Eastern scoring (web) |
| `fw2_hye` | FineWeb-2 hye_Armn train (first 3 GB of text) | Eastern | ODC-By 1.0 + Common Crawl terms | 2.42 GB | 2 | extra Eastern text for 85M / 150M; COPA measured 17 % benchmark overlap before our decontamination |
| `glotcc_hye` | GlotCC-V1 hye-Armn | Eastern | CC0 1.0 + Common Crawl terms | 1.46 GB | opt | spare Eastern web text |
| `hplt` | HPLT 2.0 cleaned hye_Armn, 8 of 44 shards | Eastern | CC0 1.0 + HPLT terms | about 1.7 GB | opt | spare Eastern web text (COPA: 10.9 % overlap) |
| `culturax` | CulturaX hy, part 0 | Eastern | mC4 (ODC-By) + OSCAR terms; **gated** | 1.88 GB | opt | spare; needs the terms accepted on HF and `HF_TOKEN` in Colab Secrets |

Download totals: **smoke 0.11 GB, core 2.69 GB, full 6.44 GB** (`python3 -I mp_data.py plan --profile <p>` prints the list; the notebook prints it in cell 7 and fetches
nothing until `I_APPROVE_DOWNLOADS` is ticked).

Tokenizer files for the bill (`mp_tok.py`, pinned revision + the sha256 measured from the official file): Mistral Nemo (Tekken), Nemotron Nano 9B v2, DeepSeek V3, Qwen 2.5,
Gemma 3 (gated), Llama 3.2 (gated); tiktoken o200k and cl100k. For the two gated ones the notebook uses `HF_TOKEN` if hagopjay has accepted the licences; otherwise, with
`ALLOW_MIRRORS`, the unsloth copies, **only if byte-identical (sha256) to the official files**; otherwise the row is skipped and says why.

## Looked for and not used

| what | why not |
|---|---|
| NVIDIA Nemotron datasets (Nemotron-CC v2 / v2.1, Nemotron-SFT-Multilingual v1 / v2, Pretraining-Specialized) | **no Armenian**: the CC sets are English-centric, the multilingual SFT sets list 5 to 6 other languages. Nemotron enters through its tokenizer, which is Mistral Tekken (verified byte-for-byte by the census) |
| Eastern Armenian National Corpus (~110M tokens) | search interface only, no bulk licence; its public-domain library is `pd_lit` |
| Matenadaran digitisations | rights and access are an institutional question (the church / institutions track) |
| Grabar Bible beyond the UD Gospels; TITUS `koriw` | licences unclear; not used until a rights holder agrees |
| Diaspora newspapers (Aztag, Asbarez, Nor Haratch, Agos ...) | copyrighted; the participation track asks publishers for consent |
| `k-mktr/western_armenian_hy`, `k-mktr/armenian_bible_hy`, several HF uploads | no licence stated |
| COPA-AI ArmSTEM, Metric-AI benchmarks | instruction / test data, not pretraining text; Metric-AI sets are mostly unlicensed or CC BY-NC |

## Processing (`mp_data.py`, rules frozen in `PREREG.md`)

1. **Evaluation sets first**: UD test splits (E ArmTDP, E BSUT, W, G), ArmWeb test_iid (first 4 MB), FineWeb-2 hye test (first 4 MB), FineWeb-2 hyw test (classifier-confirmed
   Western), held-out Western Wikipedia (2 % of article ids), MultiBLiMP.
2. **Decontamination**: any training document sharing a 13-word sequence with a long evaluation text, or an 8-word sequence with a short one (UD test sentences, MultiBLiMP,
   the landing's two texts, the UDHR), is dropped. In the dry run this removed 14 of 94 CAVaL Gospel chapters: the synoptic Gospels repeat each other's verses.
3. **Cleaning**: Unicode NFC; documents under 200 characters or under 60 % Armenian letters are dropped; exact duplicates (normalised text) removed across sources.
4. **Variety**: a character 1-4-gram naive Bayes trained on the UD train splits labels every document E / W / G (99.0 / 99.2 / 100 % on single UD test sentences, measured in
   the dry run). Source labels are kept and compared.
5. **Spelling**: a transparent marker score (classical: -ութիւն, եւ, իւ, եա, inner է, ոյ; reformed: -ություն, և, յու, ույ) labels each document classical / reformed / unclear.
6. **Pools**: Eastern, Western, Grabar (`pools/*.jsonl`), each document with its source and spelling label.
7. **Mixture at training time**: Western `min(0.5, 4 x W / T)`, Grabar (only `-G`) `min(0.25, 4 x G / T)`, Eastern the rest; the run's `meta.json` records the epochs per pool.

## Known limits (say them before a funder asks)

* **Dialect and spelling are confounded in the labels.** UD Western is in classical spelling, UD Eastern in reformed spelling; Iranian Armenians write Eastern in classical
  spelling, and much diaspora Eastern does too. A classifier trained on UD can learn spelling, not dialect. The dry-run cross-table shows it plainly (E = reformed, W = classical,
  G = classical). The first annotation task (dialect and spelling labelled separately by speakers) exists to break this.
* **Western web text is labelled by GlotLID**, which separates hye / hyw by the same cues. How much of FineWeb-2 `hyw` is Western in a speaker's sense is unknown until the
  annotation sample is labelled.
* **Grabar**: the only open, licensed Grabar text at hand is the UD Gospels (non-commercial) and whatever Wikisource holds. The `-G` arm is a pilot, not a Classical model.
* **News-heavy Eastern**: ArmWeb is news; Wikipedia and the public-domain literature add other registers, but the Eastern model will read like a newspaper.
* **No personal data is collected.** Web corpora can contain names of public figures and occasional personal details; ArmWeb drops author names. No contributor data enters
  the corpus (see `participation/`).

## Redistribution

The notebook trains on these sources and publishes **models, metrics and figures**, not the corpora. Any release of model weights inherits obligations: attribution for ODC-By
and CC BY(-SA) sources, and **non-commercial** for the `-G` models (CAVaL). The main grid's models (`bytes`, `bpe`, `mashtots` without `-G`) see no non-commercial
text in training, **but the tokenizers do**: their training sample is 10 % Grabar (in practice mostly CAVaL) and the suffix inventory is learned from all four UD treebanks.
Before any commercial release, retrain the tokenizers without CAVaL (skip `ud_caval` in `mp_tok.balanced_sample` and `mp_tok.learn_suffixes`; not yet a switch) and say so.
