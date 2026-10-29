# Annotation tasks (first two), and how their quality is checked

Tool: `annotate.html`, one file that runs in any browser with no server and no account. The coordinator sends a volunteer the HTML file and a batch file
(`batch_b001.json`, written by the notebook's data cell from the run's own pools). The volunteer works offline and presses **Save my answers**, which downloads
`labels_<batch>_<random code>.json`; they send that file back the way the consent form says. Answers stay in the browser between sessions (`localStorage`) until saved.

**No personal data enters the labels.** The form's only identifier is a random code it makes itself (`anon-xxxxxxxx`). Names for credit are collected separately on the
consent form and stored apart from the labels (see `GOVERNANCE.md`). Volunteers should not type names, addresses or anything about themselves in the note field; the
coordinator checks notes before anything is shared.

## Task 1: which Armenian, and which spelling (`dialect_spelling`)

For one sentence:

| field | values | meaning |
|---|---|---|
| `dialect` | `E` Eastern, `W` Western, `G` Classical (Grabar), `M` mixed, `D` another dialect (say which in the note), `X` not Armenian / can't tell | the variety a speaker hears, **regardless of spelling** |
| `spelling` | `classical` (Mesropian), `reformed` (1922/1940), `mixed`, `unknown` | how it is written, **regardless of variety** |
| `confidence` | 3 sure, 2 fairly sure, 1 guessing | |
| `note` | free text | for example "Western words, Eastern spelling", "Iranian Armenian", "OCR errors" |

**Why two separate questions.** Every automatic label we have mixes them up: the Western treebank is in classical spelling and the Eastern ones in reformed spelling, so a
classifier trained on them may learn spelling, not dialect. Iranian Armenians, and much of the diaspora, write *Eastern* in *classical* spelling. Human labels that keep the two
apart are the only way to measure how much of the "Western" web text is Western in a speaker's sense, and they decide how the training mix is weighted next time.

**Guideline examples** (to be checked and extended by the Western-speaking coordinator before the first real batch):
* Western markers: `կը` / `կ՚` before the verb (կ՚ուզեմ), `պիտի`, the ablative `-էն`, `ըսել`, `հոս`, `հիմա`, `ան` as "he / she".
* Eastern markers: the present with `եմ / ես / է` after a participle (ուզում եմ), the ablative `-ից`, the locative `-ում`, `ասել`, `այստեղ`, `հիմա`, `նա`.
* Classical spelling: `-ութիւն`, `եւ`, `իւ`, `եա`, `է` inside a word; reformed: `-ություն`, `և`, `յու`, `ույ`.
* Grabar: case endings and verbs of the Classical language (`եղիցի`, `զ-` before a definite object, `-ոյ`, `-աց` plurals). A modern text in classical spelling is **not** Grabar.

## Task 2: cut a word into its parts (`morph`)

For one word, shown with the sentence it came from: click between two letters to cut. The parts are the stem and each ending (plural, case, article, possessive, verb
ending). `It has no parts` if nothing can be cut off; `Not sure` to flag it. The form does not allow a cut inside `ու`: it is one vowel, which Mashtots wrote with two letters.

| field | meaning |
|---|---|
| `cuts` | letter offsets of the cuts, e.g. `[5]` for `Կարդա|լուց` |
| `segments` | the parts, e.g. `["Կարդա", "լուց"]` |
| `no_parts`, `unsure` | flags |

**Why.** The `mashtots` tokenizer cuts words at their endings using an inventory learned from treebank lemmas plus a hand list (`mp_tok.HAND_SUFFIXES`). Human cuts give a
real gold standard for Eastern and Western (the treebank lemma split is only a proxy: it finds one stem boundary and nothing else) and a better suffix inventory, above all for
Western endings that are rare in news text.

## Quality control

* **Hidden checks.** About 7 % of the dialect items are treebank sentences of known variety (their answers and every item's source are in `batch_b001.KEY.json`, which is
  never given to annotators; the batch shows no sources). Morph items carry the treebank's stem boundary in the key.
* **Overlap.** Each batch goes to at least two people; agreement is Cohen's kappa per field (dialect, spelling) and boundary F1 for words.
* **Thresholds (to start with).** An annotator's labels are used when their hidden-check accuracy on dialect is at least 80 % and their kappa with the others is at least 0.6;
  otherwise the coordinator talks with them before the labels are used. Nobody is told they "failed": disagreement is often a real dialect question, and those items go to
  the scholars' adjudication list.
* **Adjudication.** Items with disagreement go to a scholar or the coordinator; the decision and its reason are stored with the item.
* **Versioning.** Batches are numbered (`b001`, `b002`, ...); labels are never overwritten, only added with a date; a release of the label set is a dated snapshot.

## What the labels change in the model (the loop back)

1. Dialect / spelling labels: re-estimate the share of true Western text in each web source, retrain the variety classifier on human labels, re-weight the next training mix,
   and report the Western gap again. Measurable: bpb_W of the next run, classifier accuracy on held-out human labels.
2. Morph cuts: a gold boundary set for Eastern and Western; the suffix inventory is rebuilt from it and the `mashtots` tokenizer retrained. Measurable: boundary F1 against
   human cuts, tokens per word, and H2 again.
3. Both appear in the demo: the X3D scene can show a word being cut the way the volunteers cut it, and the credit roll names those who asked to be named.

## Batches for schools

Class batches are smaller (50 sentences) and use only Task 1. The teacher runs the form on the class's computers, answers are saved under one class code, and credit goes to
the class and school (no pupil names anywhere; see `CONSENT-AND-CREDIT.md`).

**The Armenian wording of the form and these guidelines must be checked by a native Western and a native Eastern speaker before the first real batch.** I wrote the interface
labels in classical spelling for the diaspora audience; they have not been reviewed.
