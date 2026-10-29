# `mashtots_model_export.json` (schema `mashtots-export/1`)

Written by notebook cell 15 (`mp_export.py`) to `results/` and Drive. Selection rules are fixed in `PREREG.md` section 6. An X3D scene (a new one; `../mashtots-landing/` is
read only) can load it in place of the landing's three authored heads. A dry-run copy (tiny model, meaningless numbers) is at `examples/mashtots_model_export.DRYRUN.json`.

| key | shape | meaning |
|---|---|---|
| `schema`, `version`, `built`, `grade` | strings | `grade` is `Measured`, or `DRY RUN ...` for the local test |
| `prereg_sha256` | string | hash of the frozen `PREREG.md` |
| `letters` | 38 objects | `index` 0-37, `ch` (upper case), `lower`, `numeral` (Ա = 1 ... Ք = 9000; null for the later two), `mashtots` (true for the 36) |
| `letters_model` | object | which run gave the letter-level data (`bytes` arm): params, tokens, bpb (E+W), layers, heads, windows used |
| `attention.letter_attention` | L x H x 38 x 38 | mean attention from a byte inside letter i to a byte inside another occurrence of letter j, pairs at most 64 bytes apart, case folded |
| `attention.pair_counts` | 38 x 38 | how many byte pairs each cell averages (low counts = noisy cells) |
| `attention.structure` | L x H | `1 - mean row entropy / ln 36` of the row-normalised 36 x 36 map |
| `attention.selected_heads` | 3 objects | `layer`, `head`, `structure`: the three most structured heads, at most one per layer |
| `attention.selected_row_normalised` | 3 x 36 x 36 | those heads' maps, each row summing to 1 (the landing's convention: `ATT` tile rows) |
| `attention.mean_row_normalised` | 36 x 36 | all heads averaged, row-normalised |
| `embeddings.contextual` | `pca3` 38 x 3 (scaled to -1..1), `explained`, `cosine36` 36 x 36, `occurrences` | the bytes model's last-layer state after each letter's last byte, averaged per letter |
| `embeddings.input` | `pca3`, `explained`, `cosine36`, `token_ids` | the `mashtots` model's input embedding of each lower-case letter (letters are tokens there) |
| `token_model` | object | which `mashtots` run gave `embeddings.input` and the token pieces |
| `probes.proverbs_1_2`, `probes.lords_prayer` | objects | the landing's two texts, exactly as its atlas writes them |
| `probes.*.upper`, `.text`, `.glyphs` | strings / list | upper-case original, the lower-case text the models read, one entry per character (spaces included) |
| `probes.*.landing_slot` | list | for each character, its glyph slot in the landing (spaces are null; Proverbs 1:2 has 46 slots, as `NG` in the landing) |
| `probes.*.surprisal_bits` | list | per character, bits the bytes model spent on it (sum over its bytes) |
| `probes.*.attention_selected` | 3 x n x n | per selected head, character-to-character attention (mean over the query character's bytes, sum over the key character's) |
| `probes.*.token_model` | `pieces`, `surprisal_bits` | how the `mashtots` tokenizer cuts the text, and the bits per piece |

Notes for the scene
* Upper and lower case are folded: the stone and the atlas are upper case, the models read lower case.
* `ու` is two letters (Ո, Ւ) here, as in Mashtots' alphabet.
* A letter's attention to its own second byte is excluded. Row normalisation turns "where does this letter look" into the landing's map; the raw means in
  `letter_attention` are what to use for a graph's edge weights (symmetrise as the landing does: `(a_ij + a_ji) / 2`).
* Every number is from a model of at most 150M parameters trained on at most 1.5B tokens; the scene's caption should say which run (`letters_model.run`) and its grade.
