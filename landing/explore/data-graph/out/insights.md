# Armenian, measured: three questions (corpora on disk; every number Measured)

## 1. Fifteen centuries

| era | words | letters | top 5 | fastest mode, vowel side | agrees with the vowel flags |
|---|---:|---:|---|---|---:|
| Grabar (CAVaL) | 73,445 | 342,533 | ԱՆԵԻՈ | ԱԵԷԸԻՈ | 97% |
| Eastern (ArmTDP) | 82,056 | 525,907 | ԱՆՐՈԵ | ԱԵԷԸԹԻՈ | 94% |
| Western (ArmTDP-hyw) | 100,396 | 580,726 | ԱՆՐՈԵ | ԱԵԷԸԻՈ | 97% |

| pair | letter frequencies (Spearman) | bigram rows (Pearson) |
|---|---:|---:|
| Grabar (CAVaL) vs Eastern (ArmTDP) | +0.841 | +0.863 |
| Grabar (CAVaL) vs Western (ArmTDP-hyw) | +0.829 | +0.890 |
| Eastern (ArmTDP) vs Western (ArmTDP-hyw) | +0.943 | +0.892 |

## 2. Does the alphabet's order carry structure? (Grabar)

Co-occurrence against closeness in the alphabet: Spearman -0.109; under 2,000 random orders -0.000 ± 0.058; p = 0.9665.
Same row of the stone (the decades) against different rows: mean co-occurrence share 0.00057 against 0.00086.

## 3. What machines charge (tokens per word)

| tokenizer | Grabar (CAVaL) | Eastern (ArmTDP) | Western (ArmTDP-hyw) | English (UDHR) |
|---|---:|---:|---:|---:|
| Mistral Nemo (Tekken) | 3.10 | 3.15 | 3.39 | 1.15 |
| DeepSeek V3 | 3.89 | 4.50 | 4.34 | 1.12 |
| gpt-oss (o200k-based) | 2.68 | 2.73 | 2.77 | 1.13 |
