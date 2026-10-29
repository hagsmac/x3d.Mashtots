# Mashtots PoC notebook (hand-over, 2026-10-29)

Where: ~/Projects/x3d/work/mashtots-poc/ (README.md indexes everything). Notebook mashtots_poc.ipynb build v1 3297217c; local dry run passes (16/16 code cells, 53 s).
Nothing downloaded, uploaded or run on the G4 yet. Not a git repo.

Owner's decisions: all four claims; Eastern = Western weight (equal in eval, Western upsampling capped at 4 repeats); Grabar with/without arms; full tokenizer x size grid
(bytes / bpe / mashtots x 6M..150M); ~150 units (units/hour unknown: notebook projects cost after a measured benchmark); dialect+spelling and morpheme tasks; static form;
licence for contributions "decide later"; audiences incl. an art submission (X3D piece from the real attention).

Findings worth knowing elsewhere
- NVIDIA Nemotron datasets contain no Armenian; Nemotron = Tekken tokenizer only.
- FineWeb-2 has hyw_Armn (265 MB parquet), GlotCC hyw (44 MB), Western Wikipedia 27 MB: Western is scarce but not absent (GlotLID labels, unverified).
- COPA-AI/armweb (ODC-By, 3.1 GB, decontaminated, held-out splits) is the best Eastern source; their 410M ablation ~0.53 bpb.
- catherinearnett/classical_armenian_pd is mislabelled: 19th-20th c. Eastern literature, not Grabar. UD CAVaL = Grabar Gospels, CC BY-NC-SA.
- Deck's UDHR ratios: o200k/Tekken reproduce within 1 %, others 2-5 % high under every segmentation tried; all within 5 %.
- UD Western is classical spelling, UD Eastern reformed: a classifier trained on them can learn spelling, not dialect.
Export JSON (EXPORT-SCHEMA.md) matches the landing's 46 Proverbs slots; attention inside one letter's two bytes is excluded.
