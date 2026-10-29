# Governance note (draft for discussion)

The data this project needs most (Western Armenian text and labels, and access to Classical texts and manuscripts) belongs to communities and institutions, not to the
project. This note proposes how decisions are made so that contributors keep a say in what is done with their work. It is a draft for the first partners to change.

## Who takes part, and what each brings

| group | brings | asks of the project |
|---|---|---|
| **Western Armenian speakers** (Lebanon, Syria, France, the US, Istanbul, ...) | dialect and spelling labels, morpheme cuts, texts they hold rights to | credit, a model that reads Western, a say in releases |
| **Schools** (day and Saturday schools with a Western curriculum) | class annotation batches; teachers as coordinators | a classroom tool, credit for the school, no pupil data |
| **Churches and the Mekhitarist congregations** (Venice, Vienna), the Catholicosates | liturgical and Classical texts, printed editions, rights to their publications | co-ownership of what is derived from their texts, respect for sacred use |
| **Scholars and linguists** (DALiH, UD Armenian teams, Calfa, Matenadaran researchers) | the gold standard, adjudication, Classical expertise | authorship, reproducible data |
| **Institutions** (Matenadaran, libraries, diaspora archives and newspapers) | manuscripts and archives, digitisations | control over images and texts, attribution, no commercial reuse without consent |

## Bodies

* **Steering group** (5 to 7 people): the project lead, one Western Armenian community representative, one teacher, one scholar, one church or institution representative,
  one younger diaspora member. Decides releases of data and models, the contribution licence, and partnerships. Meets quarterly; minutes are public.
* **Data stewards** (the coordinators): keep the consent forms apart from the labels, run quality control, answer withdrawal requests within 30 days.
* **Rights holders** keep a veto over anything derived from their texts.

## Rules (proposed)

1. **No personal data in any data set.** Labels carry random codes; consent forms live in a separate, access-controlled store; notes are checked before release.
2. **Every release is dated, versioned and described** (a data card like `../DATA-CARD.md`): sources, licences, who contributed (as they chose to be credited), known limits.
3. **Every number about a model carries its grade** (Measured, Established, Estimate, Conjecture), as in the PoC.
4. **Sacred and liturgical texts** are used for language modelling only with the agreement of the church that holds them, and are never used to generate imitation scripture.
5. **Commercial use** of community-contributed data and of models trained on it is decided by the steering group under the chosen licence; revenue, if any, goes first to the
   community tools (schools' materials, the annotation programme).
6. **Withdrawal** is honoured in every later release; what is already published is stated plainly.
7. **Disagreements about language** (what counts as Western, which spelling is right) are recorded as such, not settled by majority: the data keeps both answers.

## The loop back to contributors

* The demo and the art piece credit contributors by name (as they chose).
* Each label batch is followed by a short public note: what it changed in the models (for example "Western bits per byte fell from x to y"), with the grade.
* Schools receive the classroom version of the form and the results for their class.
* Rights holders receive the models' outputs on their texts before anything is published.

## Open questions for the first meeting

* The licence for contributed labels (see `CONSENT-AND-CREDIT.md`).
* Where consent forms are stored, and by whom (a partner institution is better than a private person).
* Whether the steering group should include an Eastern Armenian (Republic of Armenia) representative from the start, given that much of the data is Eastern.
* How the project relates to existing efforts (COPA-AI ArmWeb, Metric-AI, DALiH, Calfa) so that work is shared, not duplicated.
