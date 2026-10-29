# Mashtots: Armenian pays a tax to every AI. We measure it, cut it, and give the alphabet a voice.

*Draft one-pager, 2026-10-28, written before the GPU runs. Every claim carries its grade: **Measured** (we computed it), **Established** (published by others, used
inside its range), **Estimate** (projected), **Conjecture** (a claim of meaning). Lines marked ⧗ are pre-registered tests whose results arrive with the G4 run;
the forecasts were written down first (`PREDICTIONS.md`).*

## The problem

* **The token tax. Measured.** The Universal Declaration of Human Rights costs **1.5x** more tokens in Armenian than in English with OpenAI's newest tokenizer, **1.8x** with
  Mistral's (the same tokenizer NVIDIA's Nemotron models use), **2.8x** with Gemma, **2.9x** with DeepSeek, **5.6x** with Qwen, **9.1x** with Llama and **10.5x** with GPT-4's.
  An Armenian user pays more per word, fits fewer words in a model's memory, and gets a model that saw fewer Armenian words in training.
* **Western Armenian is barely there. Measured.** The largest curated Armenian corpus has about 0.1 % Western documents (COPA-AI's count, Established); NVIDIA's open
  training sets contain no Armenian at all (checked 2026-10-28). Western Armenian, the language of most of the diaspora, is listed by UNESCO as definitely endangered (Established).
* **Grabar, Mashtots' own language, is almost absent.** The only open, licensed Classical text we found is a treebank of the Gospels (non-commercial).

## What the proof of concept shows (one notebook, one GPU, about 150 compute units)

1. ⧗ **A script-aware tokenizer.** The 38 letters are atoms, words are cut at their endings. ⧗ How often it finds the stem/ending boundary compared with standard
   tokenizers (forecast: clearly more often, 85 %), and whether that buys a better model at equal compute (forecast: probably not yet at this scale, 25 %).
2. ⧗ **Small Armenian-only models** (6M to 150M parameters), Eastern and Western **weighted equally**, measured in bits per byte against the deck's scaling law
   `4.9e5 N^-0.795 + 0.439` (Established within 70M to 1B) and COPA-AI's 410M result (0.53 bpb, Established).
3. ⧗ **The Western gap, as a number**: how much worse the models read Western than Eastern, and how it moves with size. This is the number new Western text would close.
4. ⧗ **Classical text helps Classical reading**: models with and without the Gospels, scored on held-out Gospel chapters.
5. **The real model, made visible.** The model's own letter-to-letter attention and letter embeddings, exported for the X3D demo, which already shows the 36 letters,
   their numeric values and the token bill in a 204-second piece with an original score (duduk and kanun).

## Why now, and why us

* Compute is not the bottleneck. **Estimate:** a 1B-parameter Armenian model on all open Armenian text (about 5B tokens) is about 3 x 10^19 operations, roughly 100 hours of one
  modern GPU. **What is missing is text, labels and rights**, and those belong to communities: schools, churches, newspapers, archives, speakers.
* We built the participation side first: an offline annotation form that collects **no personal data**, a consent-and-credit template, and a governance draft that gives
  contributors and rights holders a say in every release.
* Everything is pre-registered, versioned and hashed, so a funder can check that the results were not tuned after the fact.

## What funding buys (Estimate; to be priced with partners)

| phase | months | what | main cost |
|---|---|---|---|
| 0 this PoC | now | the measured bill, the tokenizer test, the scaling points, the export | about 150 Colab compute units; the owner's time |
| 1 **Western Armenian at parity** | 6 | a Western-speaking coordinator; 20,000 labelled sentences and 5,000 segmented words from volunteers and schools; rights agreements with 2 to 3 diaspora newspapers; a 350M to 1B model | people (coordinator, stipends) and rights, not compute |
| 2 **Grabar and the manuscripts** | 12 | with the Mekhitarists, the Matenadaran and DALiH: Classical texts, handwriting recognition on bolorgir, a Classical model | partnerships, digitisation, scholars |
| 3 **A domain language** | open | the deck's closing idea: a sacred script as a programming language for its own texts (**Conjecture**) | research |

## For each audience

* **Art (festivals, residencies):** the X3D piece driven by a real model's attention, with the other threads' visuals and the score; a video render for submission.
* **Cultural foundations (Gulbenkian, AGBU, Hayastan All-Armenian Fund):** Western Armenian at parity, schools and parishes as partners, credit to every contributor.
* **Research grants:** a pre-registered, reproducible study of tokenization and scaling for a low-resource script, open code, a labelled Western data set.
* **Tech and compute programmes (NVIDIA, Google, Armenian tech):** a measured gap in their own tokenizers, a small model family, and a data pipeline ready for a 1B run.
* **Church and institutions:** co-ownership of anything derived from their texts, no imitation scripture, a tool that reads the Classical language.

*Contact: ____. Notebook, data card, pre-registration and forecasts: `mashtots-poc/`. Demo link: prepared, not yet published.*
