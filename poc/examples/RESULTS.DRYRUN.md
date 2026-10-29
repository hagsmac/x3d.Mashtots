# Mashtots PoC results (DRY RUN)

Built 2026-10-29 15:42:00 UTC. Every number below is **DRY RUN** unless its row says otherwise. Rules: `PREREG.md`.

> **DRY RUN.** A tiny model on a few MB of UD text on a Mac: these numbers test the plumbing and mean nothing about Armenian.

## H1 The token bill (UDHR, Armenian tokens / English tokens)

| tokenizer | ours | deck (its grade: Measured) | gap | within 5 % |
|---|---|---|---|---|
| o200k (GPT-4o, gpt-oss) | 1.52 | 1.51 | +0.7 % | yes |
| Mistral Tekken (= Nemotron Nano 9B v2, Nemotron 3 Nano) | 1.76 | 1.74 | +1.1 % | yes |
| Gemma 3 | 2.80 | 2.67 | +4.9 % | yes |
| DeepSeek V3 | 2.94 | 2.87 | +2.4 % | yes |
| Qwen 2.5 | 5.63 | 5.41 | +4.1 % | yes |
| Llama 3.2 (= Llama 3.1 vocabulary) | 9.05 | 8.73 | +3.7 % | yes |
| cl100k (GPT-4) | 10.54 | 10.15 | +3.8 % | yes |

## Our tokenizers (tokens per word on UD test sentences; stem-boundary recall / precision against UD lemmas)

| arm | vocab | Eastern | Western | Grabar | UDHR hy/en | boundary E (R/P) | boundary W (R/P) | round-trip failures |
|---|---|---|---|---|---|---|---|---|
| bytes | 257 | 14.15 | 12.92 | 10.31 | 1.95 | 1.00 / 0.06 | 1.00 / 0.07 | 0 |
| bpe | 2000 | 2.99 | 2.52 | 2.15 | 0.31 | 0.52 / 0.23 | 0.50 / 0.26 | 0 |
| mashtots | 2000 | 3.33 | 2.87 | 2.42 | 0.37 | 0.67 / 0.24 | 0.68 / 0.29 | 0 |
| bpe_morph | 2000 | 3.30 | 2.85 | 2.41 | 0.37 | 0.67 / 0.25 | 0.68 / 0.29 | 0 |
| mashtots_nomorph | 2000 | 2.98 | 2.54 | 2.16 | 0.30 | 0.52 / 0.23 | 0.53 / 0.27 | 0 |

Our tokenizers are trained on Armenian only, so their UDHR ratio says what an Armenian-first vocabulary costs English, not a like-for-like bill.

## The runs

| run | N (non-emb.) | tokens | bpb E | bpb W | bpb G | **bpb E+W** | ArmWeb test | W - E | MultiBLiMP hye / hyw | minutes |
|---|---|---|---|---|---|---|---|---|---|---|
| bpe-tiny | 0.1M | 0M | 2.077 | 2.002 | 2.155 | **2.039** | - | -0.075 | - / - | 0.0 |
| bpe-tiny-G | 0.1M | 0M | 2.094 | 2.009 | 2.102 | **2.052** | - | -0.085 | - / - | 0.0 |
| bytes-tiny | 0.1M | 0M | 6.180 | 6.162 | 6.173 | **6.171** | - | -0.018 | - / - | 0.0 |
| mashtots-tiny | 0.1M | 0M | 2.284 | 2.233 | 2.373 | **2.259** | - | -0.050 | - / - | 0.0 |

## H2 Does the script-aware tokenizer help? **FAIL**

Rule: mashtots better at the largest size with both arms and worse at none. Delta = bpb(bpe) - bpb(other), E+W equal; positive = the other arm is better.

| size | mashtots vs bpe | 95 % CI | verdict | bytes vs bpe | 95 % CI |
|---|---|---|---|---|---|
| tiny | -0.2193 | [-0.2297, -0.2097] | worse | -4.1314 | [-4.1877, -4.0854] |

## H4 Does Grabar text help Grabar? **inconclusive**

* tiny: Delta bpb_G = 0.0527 (95 % CI [0.0479, 0.0557]), better; cost on E+W +0.0125 bpb

The `-G` models were trained on CC BY-NC-SA text (UD CAVaL): they carry a non-commercial condition.

## H6 Grammar (MultiBLiMP)


## Data (counts of the dry-run data)

| pool | MB | documents |
|---|---|---|
| E | 1.2 | 153 |
| W | 1.0 | 70 |
| G | 0.5 | 80 |

Variety classifier on single UD test sentences: {'E': 0.9901, 'W': 0.9924, 'G': 1.0}.
Dialect x spelling, bytes kept: E|reformed 1.2 MB, E|unclear 0.0 MB, G|classical 0.5 MB, W|classical 1.0 MB

## Grades of the deck's figures used here

* token_bill_udhr_hy_over_en: Measured (deck)
* word_shapes: Measured (deck)
* data_law: Established (published fit); its plotted points are placeholders
* armenian_floor: Established within 70M-1B parameters, Estimate beyond
* closing: Conjecture
