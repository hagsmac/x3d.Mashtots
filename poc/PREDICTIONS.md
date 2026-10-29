# What I expect from the Mashtots PoC (written before any G4 run)

Date 2026-10-28. These are **my forecasts**, not part of the pre-registration (`PREREG.md`). They exist so that after the runs we can score how well I called it
(Brier score per forecast, published beside the results, including the ones I get badly wrong). What I have seen so far: the census numbers on this Mac (the token bill, tokens
per word for big tokenizers) and a dry run with a 0.1M-parameter model on 2.7 MB of treebank text, which says nothing about Armenian models.

## Why I expect what I expect

1. **Equal tokens is not equal text.** Every arm at one size trains on the same number of *tokens* (equal compute). A tokenizer that cuts words at their endings spends more
   tokens per word, so at equal tokens the `mashtots` model reads less Armenian than the `bpe` model. bpb punishes that. The morpheme split has to buy more per token than it
   costs in text, and at 32k entries I doubt it does at these sizes. The character-level base (letters as atoms) should cost nothing, since byte-level BPE merges every letter's
   two bytes in its first few hundred merges anyway.
2. **The bytes arm reads five times less text** at equal tokens, and its context is 1,024 bytes (about 500 letters). It should lose clearly.
3. **The deck's floor was fitted inside 70M to 1B**, probably on models trained much longer than ours (we cap at 1.5B tokens: 10 tokens per parameter at 150M).
   Below 70M its formula climbs fast (2.44 bpb at 6M), faster than small models really are. Inside its range, our under-trained models should sit above it.
4. **Western has a quarter to a third of the training share it should** under equal weighting (the 4-epoch cap binds), so its bpb should trail Eastern, more so at larger sizes
   where data matters more. But Western Wikipedia is encyclopedic and narrower than ArmWeb news, which may hide part of the gap.
5. **Grabar is a different language for a modern model.** Even 1 to 2 % Gospel text in training should cut Grabar bpb a lot on held-out Gospel chapters, at almost no cost to
   Eastern and Western.

## Forecasts

| # | Statement | Probability |
|---|---|---|
| O1 | The doctor cell shows ALL GOOD on the G4 on the first try | 70 % |
| O2 | The smoke profile runs to DONE without a fix from me | 55 % |
| O3 | The core run's wall time for cell 13 is within 30 % of cell 12's projection | 65 % |
| O4 | The full grid (3 arms up to 150M) needs more than 10 hours of cell-13 time | 60 % |
| D1 | Our classifier calls at least 70 % of the FineWeb-2 `hyw` test documents Western | 60 % |
| D2 | Between 0.1 % and 3 % of ArmWeb training bytes are classified Western | 65 % |
| D3 | Decontamination removes under 2 % of Eastern web documents (ArmWeb is pre-cleaned; FineWeb-2 will lose more) | 70 % |
| T1 | At 32k entries, `mashtots` spends **more** tokens per Eastern UD word than `bpe` | 70 % |
| T2 | `mashtots` beats `bpe` on stem-boundary recall by at least 0.10 on Eastern and on Western | 85 % |
| T3 | Our `bpe`'s first multi-letter Armenian merge is `ու` | 45 % |
| L1 | **H2 PASS**: `mashtots` has lower bpb (E+W) than `bpe` at the largest size, with the CI above zero | 25 % |
| L2 | `bytes` is worse than `bpe` at every size (CI below zero) | 90 % |
| L3 | At 6M, every arm's ArmWeb-test bpb is below the deck's extrapolated 2.44 | 95 % |
| L4 | At 150M (`bpe`), ArmWeb-test bpb within 10 % of the deck's 0.593 ("consistent") / more than 10 % above ("worse") | 30 % / 60 % |
| L5 | At 40M (`bpe`), ArmWeb-test bpb lies between 0.70 and 1.00 | 55 % |
| L6 | The Western gap bpb_W - bpb_E is positive for every `bpe` run of 40M and above | 70 % |
| L7 | **H4 PASS** (Grabar text helps Grabar at 15M and 40M, at most 0.01 bpb cost on E+W) | 75 % |
| L8 | MultiBLiMP accuracy of the largest `bpe` model is above 0.60 for `hye` / for `hyw` | 60 % / 50 % |
| L9 | A 4-point fit for `bpe` gives an asymptote E between 0.30 and 0.60 bpb | 40 % |
| X1 | In the export, at least one of the three selected heads has structure above 0.20 | 50 % |

## What would change my mind

* `mashtots` clearly better at equal tokens: the morpheme pieces are worth more than the text they cost, which would be the strongest funding claim in the PoC.
  I would then run the same comparison at equal *bytes* to separate the two effects before saying so.
* `bytes` competitive at 40M+: suspect the bpb denominator or the 0xFF document separator before believing it.
* Our 150M below the deck's curve: the deck's fit is conservative, or our eval set is easier than its panel. Check the eval set first.
* A negative Western gap everywhere: the Western sets are easier, not the Western model better. Look at the per-set table before saying anything about Western.
