# Mashtots PoC: pre-registration (frozen by the notebook before any model trains)

Version 1, 2026-10-28. The notebook's Freeze cell stores the sha256 of this file and of the code that governs the analysis (`mp_analyze.py`, `mp_eval.py`,
`mp_train.py`, `mp_model.py`, `mp_tok.py`, `mp_data.py`, `mp_export.py`) before the first training step. Changes after that go into `DEVIATIONS.md` with the reason
and the date; the frozen rules are still reported.

## 1. Grades

Every number in the results carries one grade. **Measured**: computed in this run from the data and code named here. **Established**: published by others and used inside the
range where it was established. **Estimate**: extrapolated, projected, or a published figure used outside its range. **Conjecture**: a claim of meaning that no number here tests.
A local dry-run number is `DRY RUN` and never leaves the notebook's own output.

## 2. Data rules

* Evaluation sets are built first (section "eval" of `data_stats.json`); every training document that shares a 13-word sequence with any long evaluation text, or an 8-word
  sequence with a short one (UD test sentences, MultiBLiMP sentences, the probe texts, the UDHR), is dropped.
* Variety of a training document = the prediction of the character 1-4-gram naive Bayes classifier trained on the UD train splits (E = ArmTDP + BSUT, W = Western ArmTDP,
  G = CAVaL). The source's own label is recorded and the agreement is reported. Known confound: UD Western is in classical spelling, UD Eastern in reformed spelling, so the
  classifier may separate spelling, not dialect; a dialect x orthography cross-table is reported, and no claim about Western is made from classifier-labelled data alone
  beyond "the classifier calls it Western".
* Western evaluation from FineWeb-2 keeps only the documents the classifier calls Western.
* Exact duplicates (normalised text) are removed across all sources; the first copy in source order is kept.

## 3. Training rules

* Arms `bytes`, `bpe`, `mashtots` (definitions in `mp_tok.py`), all at sizes 6M, 15M, 40M (core) and 85M, 150M (full), non-embedding parameters.
* Every arm at one size gets the same number of training tokens, `T = min(20 N, 1.5e9)`, the same batch size in tokens, the same learning-rate schedule (warm-up 5 %,
  cosine to 10 %), and the same seed (405). One seed per configuration (budget); seed variance is not measured, which section 5 accounts for by testing over documents.
* Mixture per sequence: Western with probability `p_W = min(0.5, 4 W_tokens / T)`, Grabar (only in `-G` runs) with `p_G = min(0.25, 4 G_tokens / T)`, Eastern otherwise.
* Grabar arm: `bpe` at 15M and 40M, with (`-G`) and without Grabar training text; everything else equal.

## 4. Measures

* **bpb** per evaluation set (`mp_eval.py`): text-token negative log-likelihood in bits over UTF-8 bytes; `<eos>` is context, never a target.
* `bpb_E`, `bpb_W`, `bpb_G` = unweighted means over that variety's sets; **headline `bpb_EW` = (bpb_E + bpb_W) / 2** (Eastern and Western weighted equally, the owner's decision).
* **Deck comparison** uses `E_armweb_test` (news, the domain closest to the published Armenian results); `bpb_EW` is reported beside it.
* MultiBLiMP accuracy = share of pairs where the grammatical sentence gets the higher total log-probability (first 2,000 pairs per language).
* Tokenizer measures: tokens per whitespace word on UD test sentences per variety (95 % bootstrap CI over sentences), UDHR Armenian / English token ratio, stem-boundary
  recall and precision against the UD lemma split (a word's stem boundary is the length of its shared prefix with its lemma, for inflected content words).

## 5. Hypotheses and decision rules

**H1 token tax (descriptive).** Report the UDHR Armenian / English ratio for the eight big-lab tokenizers. "Reproduces the deck" for a tokenizer if within 5 % of the deck's
figure; any larger gap is reported as is.

**H2 the script-aware tokenizer helps.** For each size s with both runs finished: Delta_s = bpb_EW(bpe) - bpb_EW(mashtots), with a 95 % CI from a paired bootstrap over evaluation
documents (2,000 resamples; each set resampled within itself; E and W sets weighted as in bpb_EW). `mashtots` is **better at s** if the CI lies above 0, **worse** if below 0,
else **no difference**. **H2 PASS** if `mashtots` is better at the largest size that finished for both arms and at no size worse. **H2 FAIL** if it is worse at the largest size.
Otherwise **inconclusive**. The same test is reported for `bytes` vs `bpe` (expected: bytes worse at equal compute).

**H3 the floor.** For each arm with at least 4 finished sizes, fit `bpb(N) = A N^-alpha + E` (least squares in log bpb; bounds A > 0, 0 < alpha < 2, 0 <= E < 2) on
`E_armweb_test` and on `bpb_EW`. Compared with the deck's `4.9e5 N^-0.795 + 0.439`:
* inside 70M to 1B (our 85M and 150M points): **consistent** if our bpb is within 10 % of the deck's value at that N; **better** / **worse** otherwise.
* below 70M: the deck's curve is an Estimate there; the deviation is reported, and nothing is concluded about the deck from it.
* With fewer than 4 sizes (core), points only, no fit.

**H4 Grabar text helps Grabar.** For 15M and 40M: Delta_G = bpb_G(bpe) - bpb_G(bpe-G), paired bootstrap over Grabar evaluation documents. PASS if the CI lies above 0 at both
sizes and bpb_EW of the `-G` model is not worse by more than 0.01.

**H5 the Western gap (descriptive).** bpb_W - bpb_E per run, and how it moves with size.

**H6 grammar (descriptive, with a test).** MultiBLiMP accuracy per language for every finished run; one-sided binomial test against 0.5 for the largest run of each arm.

## 6. The X3D export (selection rules fixed now, so the art is not cherry-picked)

* Models: the largest finished `bytes` model (letter-level attention: a letter's two UTF-8 bytes are positions of their own) and the largest finished `mashtots` model
  (letters are tokens: their input embeddings are exported).
* Letter attention: over the first 200 windows of 512 positions from `E_armweb_test` and the first 200 from `W_wiki_heldout` (the UD Eastern and Western test sets
  when those are absent), for every layer and head, A[i, j] = mean attention
  that positions inside an occurrence of letter i put on positions inside another occurrence of letter j (a letter's attention to its own second byte
  is excluded), over pairs at most 64 positions apart, for the 36 letters (upper and lower case folded; the two later letters exported separately). Row-normalised copies as the landing uses.
* The three heads shown are those with the highest structure `1 - mean row entropy / ln 36` on the row-normalised map, at most one per layer; ties by layer order.
* Embeddings: contextual (mean last-layer state over the letter's occurrences) from the `bytes` model, input embeddings from the `mashtots` model; 3-D PCA of each; cosine 36 x 36.
* The probe texts are exactly the landing's (Proverbs 1:2 and its Lord's Prayer lines); per glyph: surprisal in bits and the three heads' attention to earlier glyphs.

## 7. What would make me distrust the results

* A round-trip failure in any of our tokenizers (the bpb denominators would be wrong): stop.
* Any run with a non-finite loss, or a final training loss above the 6M run's of the same arm: report, do not fit.
* `bytes` beating `bpe` at 40M+ at equal compute: suspect the bpb code before believing it.
* Contamination: more than 5 % of the documents of any eval set found again in training after decontamination (spot check in the analysis cell).
