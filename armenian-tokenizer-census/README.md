# Armenian tokenizer census (2026-10-27)

Tokens per word for 8 tokenizers (9 rows; gpt-oss's `tokenizer.json` repeats o200k and is folded into its row below) on four Armenian treebank registers. CPU only, nothing trained, nothing spent.
Run: `TIKTOKEN_CACHE_DIR=$PWD/data/tiktoken python3 -I census.py data out` (after `fetch_tokenizers.py` and the downloads below). Results: `out/results.md`, `out/results.json`.

## Result (tokens per whitespace word, 95% bootstrap CI over sentences)

| tokenizer | vocab | Eastern (ArmTDP) | Eastern (BSUT) | Western | Grabar | UDHR hy/en | folder table (EA, UDHR) |
|---|---|---|---|---|---|---|---|
| o200k (GPT-4o, gpt-oss) | 200,019 | 2.64 [2.62-2.66] | 2.47 | 2.83 | 2.72 | 1.52x | 2.64, 1.51x |
| **Nemotron 3 Nano 30B** | 131,072 | 2.99 | 2.83 | 3.40 | 3.09 | 1.76x | not in folder |
| **Nemotron Nano 9B v2** | 131,072 | **2.99** [2.97-3.01] | 2.83 | 3.40 | 3.09 | 1.76x | not in folder |
| Mistral Nemo (Tekken) | 131,072 | 2.99 [2.97-3.01] | 2.83 | 3.40 | 3.09 | 1.76x | 2.99, 1.74x |
| Gemma 3 | 262,145 | 4.13 [4.11-4.15] | 3.96 | 4.23 | 3.73 | 2.80x | 4.15, 2.67x |
| DeepSeek V3 | 128,815 | 4.36 [4.33-4.39] | 4.15 | 4.45 | 3.96 | 2.94x | 4.38, 2.87x |
| Qwen 2.5 | 151,665 | 7.58 [7.54-7.62] | 7.39 | 7.08 | 5.83 | 5.63x | 7.66, 5.41x |
| Llama 3.2 (3.1 vocab) | 128,256 | 12.22 [12.15-12.28] | 11.86 | 11.49 | 9.42 | 9.05x | 12.33, 8.73x |
| cl100k (GPT-4) | 100,277 | 13.93 [13.85-14.01] | 13.56 | 13.03 | 10.60 | 10.54x | 14.07, 10.15x |

Corpora: ArmTDP Eastern 5,527 sentences / 82,648 words; BSUT Eastern 2,523 / 36,829; Western ArmTDP 6,644 / 99,130; Grabar CAVaL 4,781 / 72,962 (all splits, UD master as of today). Full CIs for every cell are in `out/results.md`.

## Findings
1. **Verified: Nemotron Nano 9B v2 uses the Tekken tokenizer.** Same 269,443 merges in the same order, same ids for every shared token; only 4 special tokens differ (`verify_nemotron_vs_tekken.py`, `out/verify_nemotron_vs_tekken.txt`). So it needs about 28% fewer tokens per Eastern Armenian word than Gemma 3 (2.99 vs 4.13): the same context window holds about 38% more Armenian words. **Update:** Nemotron 3 Nano 30B-A3B (17 MB tokenizer.json, downloaded on your OK) gives identical counts in every column; its vocabulary is Tekken too (131,072 entries, 131,064 shared with Mistral Nemo, 0 with different ids). Not checked: Nemotron 3 Super / Ultra and the 12B v2 models.
2. **Replication of the folder table.** Eastern words per token: all seven shared tokenizers within 1.1% of the folder's numbers (Tekken and o200k exact). UDHR ratios are 1% to 5% higher than the folder's for the larger-ratio tokenizers (Gemma 2.80 vs 2.67, cl100k 10.54 vs 10.15). I do not know how the folder segmented the UDHR; mine is every `<para>` in the preamble and articles, 61 Armenian and 60 English paragraphs, so the ratio is the less trustworthy column.
3. **Harness cross-check.** The tiktoken o200k path and the HF `tokenizers` path on gpt-oss-20b's `tokenizer.json` give identical counts in every column, so the two code paths agree.
4. **Register penalty differs by tokenizer.** Western vs Eastern (ArmTDP): Tekken +14%, o200k +7%, Gemma 3 +2%, DeepSeek +2%, and the byte-heavy vocabularies (Qwen, Llama, cl100k) -6% to -7% (cheaper). Grabar vs Eastern: Gemma 3 -10%, Tekken +3%, o200k +3%. Two Eastern treebanks differ by 3% to 7% within one tokenizer (ArmTDP vs BSUT), so register differences under about 7% are inside the genre noise (Western +2% on Gemma/DeepSeek is not a finding).

## What this does and does not show
- Fertility is not competence. The folder's own note cites a Tajik study where the GPT-OSS tokenizer was efficient and the model still scored well below Gemma 3. Nothing here says Nemotron Nano 9B v2 can read Armenian: Armenian is not in its listed languages, and no model was run.
- Gemma 3 stands in for Gemma 4 (the base arm-gemma-e4b uses); I did not download the Gemma 4 tokenizer. COPA's paper reports 4.15 for the Gemma family, which matches.
- Corpora are UD treebanks (news, Wikipedia, fiction, Bible for Grabar, mixed); word = whitespace token with punctuation attached. A corpus-size estimate from this (ArmWeb 789M words x 2.99 = about 2.4B Tekken tokens vs 3.3B Gemma tokens) is an inference, not measured on ArmWeb.
- Whether Tekken's lower fertility helps or hurts continued pretraining is open; the paper found vocabulary extension hurt at 2B tokens, but that is a different intervention from choosing a base with a better stock tokenizer.

## Data fetched (all public; each in its own folder under `data/`, read only as data)
UD_Armenian-ArmTDP 13 MB, UD_Armenian-BSUT 5.9 MB, UD_Western_Armenian-ArmTDP 15 MB, UD_Classical_Armenian-CAVaL 12 MB (raw.githubusercontent.com/UniversalDependencies, master); `udhr/` 44 KB (eric-muller/udhr on GitHub; unicode.org no longer serves it at the old path);
`tokenizer.json` only: nvidia/NVIDIA-Nemotron-Nano-9B-v2 (17 MB), openai/gpt-oss-20b (28 MB; bigger than I said), mistralai/Mistral-Nemo-Instruct-2407 (9.3 MB), deepseek-ai/DeepSeek-V3 (7.8 MB); tiktoken o200k and cl100k BPE files (5.3 MB, hash-checked by tiktoken). Qwen 2.5, Gemma 3 and Llama 3.2 came from your existing Hugging Face cache. Total about 137 MB (including the Nemotron 3 Nano tokenizer, 17 MB). Treebank licences are CC BY-SA or similar per treebank; check before redistributing.

## Next (all cheap)
- Extend the harness with a corpus-specific check on ArmWeb (needs a download of COPA's data).
- Feed the register penalty into the bits-per-byte experiment on the G4.
