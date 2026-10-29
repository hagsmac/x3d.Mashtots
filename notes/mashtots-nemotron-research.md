# Mashtots / Armenian LLM: Nemotron, datasets, HTR (web research, 2026-10-27)
Read-only desk research. Nothing trained, downloaded or spent. Search-snippet level; verify before relying.

## Nemotron
- Nemotron 3: Nano (~31.6B, Dec 2025), Super (120B, Mar 2026), Ultra (550B, Jun 2026); 3.5 Lightning (Aug 2026); 3.5 Super-VL (Oct 2026). Also Nano-9B-v2, Nano-12B-v2-Base, Nemotron 3 Nano 4B.
- Licenses differ per model (NVIDIA Open Model License vs OpenMDW-1.1); sources conflict, check each card.
- Armenian is NOT in any listed supported-language set (Super: en/fr/de/it/ja/es/zh; Ultra adds hi/ko/pt-BR). No published Armenian tokenizer fertility for Nemotron found -> must measure (cheap, tokenizer files only).
- Precedent: Dicta-LM 3.0 (Hebrew) did CPT from Nemotron-Nano-12B-v2-Base on 80 H200 via NeMo (arXiv 2602.02104). Megatron Bridge verified recipe: Nemotron 3 Nano pretrain/SFT/LoRA on 1x8 H100.

## Armenian state of the art (arXiv 2609.03350, COPA, 2026-09-03)
- ArmWeb 4.37M news docs (3.3B Gemma tokens; hyw only 4,533 docs); ArmSTEM 373K EN-HY problems; arm-gemma-e4b (Gemma-4-E4B CPT, 10B tokens). Gemma chosen for tokenizer fertility 4.15 vs Qwen3.5 5.31, Llama-3.1 12.2.
- Vocab extension hurt at 2B tokens (40-45% worse BPB). Contamination: FineWeb-2-hy 17.4%, HPLT-v2 10.9%, CulturaX 7.9%, ArmWeb 3.3%.
- Corpus sizes (Gemma tokens): CulturaX-hy 4.5B, HPLT-v2-hy 5.8B, FineWeb-2-hy 2.3B.
- Benchmarks: ArmBench-LLM / ArmBench-TextEmbed (Metric AI Lab). HF org: COPA-AI. Repro code MIT.
- Cheap alternative: Trans-Tokenization (arXiv 2408.04303) adapted Mistral-7B to Armenian, 13 GPU-h on 1xA100.

## Western Armenian / Grabar data
- Text: essentially none at scale. Speech: mwa_hy (Radio Vatican, ReRooted). EANC (Eastern) ~110M tokens.
- Grabar: TITUS-2-0/armenian (GitHub; only "koriw" released), DALiH (ANR-21-CE38-0006) plans 10M-token Classical corpus + Western corpus.

## HTR / Matenadaran
- No open Matenadaran-specific HTR set found. Closest: nomikos-project/armenian-manuscript-htr (HF; 1,704 lines, 34 pages, BnF Arm.172 + UCLA MS72, PAGE-XML); Kasparian 2025 Armenian HTR guidelines; Calfa Vision (bolorgir CER 5.42%); Vidal-Gorene et al. 2024 index of digitized Armenian manuscripts; opendata.am handwritten set (91 imgs, tiny).
- Matenadaran image access / rights = human question, not solvable by desk research.

## Suggested next steps (all cheap, no GPU)
1. Measure Nemotron (Nano 4B/9B/12B, 3 Nano 30B) tokenizer tokens/word on UD Armenian + UDHR, add to the folder's fertility table (haylab scripts).
2. Check license on the chosen base; pick Gemma-4-E4B (proven) vs Nemotron-Nano-12B-v2-Base (NeMo path, Hebrew precedent).
3. Inventory Matenadaran digitization access + Calfa/NOMIKOS HTR baseline; ask owner about institutional contact.
4. Keep the confidential annotation-project note in armenian_LLM.md out of shared folders.
