# Measured letter graph (Grabar) vs the deck's authored graph

Corpus: UD Classical Armenian CAVaL (train+dev+test, # text lines): 4,781 sentences, 73,445 words, 342,533 letters, 269,088 in-word bigrams. Dropped (not among the 36): none (Օ and Ֆ never occur in this Grabar corpus).

| quantity | measured (Grabar) | deck (authored) |
|---|---|---|
| λ₂ (Fiedler value) | 0.405 | 0.488 |
| Fiedler sign vs vowel flags | 56% | 64% |
| highest mode (normalised co-occurrence, eigenvalue -0.644) sign vs vowel flags | 97% | - |
| top mode of the plain Laplacian (localised on Ա: a caution, not a result) | 97% | - |
| PageRank top 5 | ԱՆԵՈՐ | ԼՆՅ (top 3) |
| Spearman PageRank measured vs deck | +0.02 | |
| Spearman PageRank vs letter frequency | +0.95 | |
| edge-weight correlation (630 pairs) | -0.11 | |

Sukhotin (1962) finds, in order: **ԱԵՈԻԷԴԸ**; the deck flags **ԱԵԷԸԻՈՒ**; per-letter agreement 94%.

Highest mode, vowel side: **ԱԵԷԸԻՈ**. Bootstrap (200 resamples of the sentences): Ա 100%, Դ 7%, Ե 100%, Է 100%, Ը 100%, Ի 100%, Ո 100%, Ւ 0% (every other letter 0 %).

Tekken (Mistral Nemo) merges 198 two-letter Armenian pairs; the first ten, with their merge rank: ու (1,986), ան (2,247), ակ (4,608), եր (5,194), ին (5,941), այ (6,294), ար (7,325), ել (8,141), ամ (9,379), ատ (11,053).
