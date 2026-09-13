# Supervisor meeting — 31 July 2026
## Speaking notes and justification map

---

# Part 0 — Yes, the state of the art exists

**Chapter 2 is written: 14 typeset pages, 64 verified references.** It is not a
generic literature review. It is organised around your pipeline, so that every
engineering decision has a citation standing behind it.

If your supervisor asks "on what basis did you choose X?", the answer is in
Section 2.x and the citation is in the bibliography. Part 1 below is the lookup
table.

The chapter's sections, and what each one licenses you to claim:

| Section | Covers | Justifies |
|---|---|---|
| 2.2 From parametric knowledge to RAG | Lewis, REALM, FiD, RETRO, REPLUG, Self-RAG | Why an external evidence store at all |
| 2.3 Retrieval or parametric adaptation | LoRA, QLoRA, Ovadia et al. | Why RAG over fine-tuning — and why not on cost grounds |
| 2.4 Sparse, dense, hybrid | BM25, DPR, SBERT, Contriever, ColBERT, SPLADE, BGE-M3, MTEB, RRF, Bruch | Every retrieval choice, including the ones you rejected |
| 2.5 Granularity and hierarchy | Dense X Retrieval, Lost in the Middle | Parent–child chunking and the bounded context |
| 2.6 Cross-encoder reranking | Nogueira, monoT5, MiniLM, MS MARCO | The reranker, and its domain-shift caveat |
| 2.7 Legal and regulatory NLP | LEGAL-BERT, LexGLUE, CaseHOLD, LegalBench, SARA, Magesh, aeroBERT | Why legal text is a distinct domain; why grounding ≠ safety |
| 2.8 Attribution and verifiability | AIS, Attributed QA, Liu et al., ALCE, RARR | The source-ID constraint and quote verification |
| 2.9 Selective answering | Geifman, Kamath, Kadavath, R-Tuning | Abstention as a designed decision, not a threshold |
| 2.10 Evaluation | nDCG, ROUGE, Maynez, KILT, RAGAS, ARES, LLM-as-judge | Which metrics, and why ROUGE is not correctness |
| 2.11 Benchmark validity | Contamination, Cohen, Fleiss, Landis & Koch, Wilson | The review protocol and the statistics |

---

# Part 1 — Justification map

**Print this page.** If he challenges any single decision, the answer is one row away.

| Decision | Why | Authority |
|---|---|---|
| **RAG rather than fine-tuning** | Retrieval beats unsupervised fine-tuning for injecting new and time-shifted knowledge; and adapter weights cannot supply provenance at all | Ovadia et al. 2024 (EMNLP) |
| **Not dismissing fine-tuning on cost** | LoRA/QLoRA make it affordable, so the argument has to be about knowledge properties, not compute | Hu et al. 2022; Dettmers et al. 2023 |
| **Parent–child chunking** | Finer indexing granularity measurably improves retrieval, especially for rare entities — and legal meaning sits in the subparagraph | Chen et al. 2024, *Dense X Retrieval* (EMNLP) |
| **Bounded context, not "give it everything"** | Models use middle-of-context evidence unreliably and degrade as context grows, even long-context models | Liu et al. 2024 (TACL), *Lost in the Middle* |
| **Keeping BM25** | Lexical matching rewards exact identifiers, article numbers and formulaic wording — exactly what regulation is made of | Robertson & Zaragoza 2009 |
| **Adding a dense channel** | Contrastively pretrained retrievers transfer zero-shot to unseen domains; recovers paraphrase BM25 misses | Izacard et al. 2022, *Contriever* |
| **text-embedding-3-large over 3-small** | Selected on the **development split only**, before opening the test comparison | Your D014 — procedure, not literature |
| **No single "best" embedding model claim** | MTEB shows no model dominates across task families; selection must be against the target task | Muennighoff et al. 2023 (EACL) |
| **Hybrid fusion at all** | Dense and sparse are complementary, not redundant — BGE-M3's own hybrid mode beats either alone | Chen et al. 2024, *M3-Embedding* |
| **RRF specifically** | No score normalisation, no tuned parameter — so it **cannot leak** from the held-out split | Cormack et al. 2009 |
| **…and the honest caveat** | Convex score combination outperforms RRF in and out of domain; RRF discards magnitude | Bruch et al. 2024 (TOIS) |
| **Cross-encoder reranking** | Joint query–passage attention substantially outperforms independently encoded representations | Nogueira & Cho 2019; Nogueira et al. 2020 (monoT5) |
| **A small distilled reranker** | MiniLM retains most teacher performance at a fraction of cost, making full attention affordable over a top-20 pool | Wang et al. 2020 |
| **Naming its domain shift** | MS MARCO is short factoid web queries; your questions are long and regulatory. Gains are obtained **despite** shift | Nguyen et al. 2016 |
| **Retrieve 20, rerank to ~5** | A reranker cannot recover evidence absent from the pool — candidate recall is a hard ceiling | Follows from the above; your own measurement |
| **Source IDs, not model-written citations** | Retrieve-then-read beats post-hoc citation attachment on both correctness and attribution | Bohnet et al. 2022 |
| **Verbatim quote verification** | Only ~half of generated sentences are fully supported by their own citations in deployed systems | Liu, Zhang & Liang 2023 (EMNLP Findings) |
| **Citation quality reported separately** | ALCE established precision/recall on citations as separable from answer correctness | Gao et al. 2023 (ALCE) |
| **Revision before abstention** | Post-hoc targeted revision is a published alternative to regenerating or refusing | Gao et al. 2023 (RARR) |
| **Abstention at all** | Retrieval grounding reduces but does not eliminate hallucination — 17–33% in commercial legal tools | **Magesh et al. 2025 (JELS)** |
| **Abstention as risk–coverage** | Selective prediction has a formal treatment with distribution-free guarantees | Geifman & El-Yaniv 2017 |
| **Not using generator confidence** | Model confidence is badly miscalibrated under domain shift; a separate decision function does better | Kamath, Jia & Liang 2020 |
| **ROUGE demoted to continuity only** | n-gram overlap correlates weakly with human faithfulness; entailment measures correlate better | Maynez et al. 2020 (ACL) |
| **nDCG for retrieval** | Credits graded relevance and discounts by rank position | Järvelin & Kekäläinen 2002 |
| **Retrieval and generation scored separately** | KILT's provenance requirement is the precedent | Petroni et al. 2021 (NAACL) |
| **Building a fresh benchmark** | Public benchmarks are contaminated by pretraining; contamination must be documented per benchmark | Sainz et al. 2023 |
| **Human audit of AI-generated gold** | ARES: synthetic evaluation data is defensible only with human-anchored correction | Saad-Falcon et al. 2024 (NAACL) |
| **Reporting κ, not just agreement %** | Chance-corrected agreement is the standard; raw % overstates reliability on skewed labels | Cohen 1960; Fleiss 1971; Landis & Koch 1977 |
| **Wilson intervals, not normal** | Normal approximation is unreliable at small n and proportions near 0 or 1 | Wilson 1927 |

**The one-sentence version if he asks the general question:**

> "Every choice in the pipeline has a citation behind it in Chapter 2, including
> the ones I decided against — ColBERT, SPLADE, learned fusion — and the one
> place where the literature says my choice is suboptimal, which is RRF."

That last clause is what makes it credible. Volunteer it.

---

# Part 2 — Slide by slide

Each entry: **what to say** (roughly 45–60 seconds), **have ready**, **if he asks**.

---

## Slide 1 — Title

**Say:** "The project has moved from a three-system comparison to a study of
where retrieval-grounded QA fails and what a system should do about it. Today I
want to agree two things: how the benchmark gets validated, and the scope for the
last two weeks of experiments."

**Purpose:** set the agenda in the first fifteen seconds so he knows what you need
from him. Don't open with the pipeline.

---

## Slide 2 — The original number was confounded

**Say:** "My first phase reported 63 out of 100 on a loose proxy. I want to be
precise about what that number is, because it isn't correctness. Under an exact
citation-plus-content criterion it's 43. And the gap between 82 retrieved and 63
accepted is itself informative — retrieval is necessary but nowhere near
sufficient. The same baseline also had chunks of 30,000 characters while the
generator only ever saw the first 1,500. So the original figure mixes system
failure with data defects. It's a starting point, not a ceiling."

**Have ready:** 82 retrieved / 63 loose / 43 exact. The 30,275 and 1,500 numbers.

**If he asks "so was the first phase wasted?":** No — it produced the diagnosis.
Without the audit you would not know which of those three numbers to trust, and
the failure taxonomy is what motivated the repair.

**Tone:** this slide is you criticising your own earlier work before anyone else
does. That reads as rigour, not weakness. Do not sound apologetic.

---

## Slide 3 — The reframe

**Say:** "The comparison question — few-shot versus RAG versus LoRA — is a
leaderboard. It can't be causal anyway, because the three systems don't share a
base model. The more useful question is where retrieval-grounded QA fails, and
which observable condition justifies escalating to reranking, clarification, or a
human. The target is the simplest intervention that recovers the failure."

**Have ready:** Self-RAG is the closest published antecedent. The difference: it
learns the control decision inside the model; you externalise it so a compliance
reviewer can audit why the system escalated.

**If he asks "is this still an engineering project or is it research now?":**
Both. The pipeline is engineering; the escalation policy and its calibration are
the research contribution.

---

## Slide 4 — The repaired benchmark

**Say:** "The corpus is rebuilt as parent–child: 109 legal parents, 1,535
retrievable children, with articles, annexes, recitals and guidance kept distinct
across five instruments. The evaluation set is 99 questions, each tied to exact
child evidence. It's split by legal parent rather than by question ID — 42
development, 57 test, zero parent leakage."

**Have ready:** 21 records corrected, 1 excluded. Zero critical validation issues,
zero warnings, 12 parser and integrity tests passing, byte-identical rebuild.

**If he asks "why split by parent?":** Several questions come from the same
article. Splitting by question ID would put near-identical evidence in both
partitions and inflate apparent generalisation.

**If he asks "which record did you exclude and why?":** QA_0003 — generated from
table-of-contents text, its answer just points at a section number. All three
baseline systems failed its citation criterion, so removing it favours nobody. I
report both the N=100 and N=99 views.

---

## Slide 5 — Retrieval

**Say:** "Three retrieval configurations on the held-out test set. BM25 is strong
because regulation is full of article numbers and formulaic language. The dense
model recovers paraphrase. Neither alone gets there — fused, evidence is found for
54 of 57 questions at depth 20. The embedding model was selected on development
data only, before I opened the test comparison, and the fusion constant was fixed
in advance and never tuned."

**Have ready:** k=5 → BM25 73.7, dense 71.9, hybrid 80.7. k=20 → 84.2 / 86.0 / 94.7.

**If he asks "why not a multilingual model like BGE-M3?":** It's in Chapter 2 and
it's a genuine option. Given the schedule I'd rather not add a third embedding
model — I'd like your view on that, it's decision two.

**If he asks "why RRF and not a tuned combination?":** Volunteer this before he
asks. Bruch et al. show convex score combination beats RRF. I chose RRF because it
has no tuned parameter and therefore cannot leak information from the held-out
split. In a project whose central claim is about measurement validity, that
mattered more than the last increment of recall. It's stated as a limitation.

---

## Slide 6 — Reranking

**Say:** "A cross-encoder scores each query–passage pair jointly, over the fixed
top-20. Top-1 goes from 51 to 67 per cent, and at five sources — which is what the
generator actually sees — from 81 to 88. Recall at 20 is unchanged, by
construction. That invariance is the point: it separates a ranking failure from a
candidate-generation failure."

**Have ready:** 22.7M parameters, 1,980 pairs, run locally on GPU, no project text
sent to any hosted endpoint.

**If he asks about the reranker's domain:** It's trained on MS MARCO — short
factoid web queries. My questions are long and regulatory. So the gain is obtained
*despite* a domain shift, and I say so in the methodology rather than claiming a
clean transfer.

---

## Slide 7 — The three residuals ★

**This is the slide that matters. Slow down here.**

**Say:** "Three questions fail even at depth 20. It would be easy to report that
as a system ceiling of 54 out of 57. But when I looked at them individually they
turned out to be three completely different problems. QA_0063 asks 'what
exceptions?' — it's too broad, several real exception provisions compete, so the
question is ambiguous. QA_0080 has equivalent annex wording outside the single
child I labelled as gold — so my benchmark is incomplete, not the system. Only
QA_0176 is a genuine retrieval failure. Quoting 54 out of 57 as a ceiling would
have been a measurement error, not a finding."

**Then pause.** This is your best material — let it land before moving on.

**If he asks "how do you know these three are representative?":** I don't, and
that's exactly why the 33-record review samples exceptions *and* unchanged
controls. If unchanged records also turn out to be mislabelled, the problem is
broader than three cases.

---

## Slide 8 — The validity gate

**Say:** "The corrections to the benchmark were AI-assisted. That process can't
certify itself, so I built a separate gate: 33 records, covering all the audit
exceptions, the three residuals, and ten stratified unchanged controls. They're
reviewed by practising aviation professionals, under a rule I fixed and wrote down
*before* collecting any responses — minimum two raters, strict majority, and
corrections stay with me because a multiple-choice form should never write gold
data. I report agreement with Cohen's or Fleiss' kappa, and I list every contested
record individually rather than resolving it by majority."

**Have ready:** decisions D023 and D024, dated before collection.

**If he asks "why not just do it yourself?":** I can, and I'm filling the queue in
parallel so I'm not blocked. But then it's author verification of AI-assisted
curation, which is the easiest thing to attack at the soutenance. A panel gives me
a measured agreement statistic instead.

**If he asks "what if reviewers disagree?":** Then the question is demonstrably
ambiguous, which is a result. It's the same claim I make about QA_0063 — except
measured externally instead of asserted by me.

**Ask him here:** would you be willing to spot-check ten records? Thirty minutes,
and it gives me a second-rater figure.

---

## Slide 9 — The escalation ladder

**Say:** "This is the proposed contribution. Levels 0 to 6, and the interesting
part is the transition rule, not the levels. Every trigger has to be computable at
runtime — gold-label agreement isn't available in deployment, so it can't appear in
a trigger, however convenient that would be for reporting. Thresholds are
calibrated on development and applied unchanged to test."

**Have ready:** escalation *precision* — of the questions I escalated, how many
would actually have failed at the lower level. Escalation *recall* — of the
questions that failed, how many did I escalate.

**If he asks "how do you know the policy is any good?":** Because a policy that
escalates everything achieves perfect recall and is worthless. Reporting both
precision and recall is what makes the economy claim falsifiable.

---

## Slide 10 — Status

**Say, plainly:** "Retrieval and reranking are done and reproducible. Both context
variants are built. Generation has not run, and it is deliberately blocked until
the benchmark is frozen — I don't want to score answers against gold data I'm not
yet confident in. The review is at zero of thirty-three in the repository. The form
is live and the aggregation tooling is built and tested, but responses aren't in
yet. That one gate blocks all four remaining items."

**Do not soften this.** He will respect the honesty and he would find out anyway.

**If he asks "why didn't you just run generation?":** Because running it now means
scoring against unfrozen gold and then re-running everything after the freeze.
It's the same reason I selected the embedding model on development only.

---

## Slide 11 — Schedule

**Say:** "I've pulled the full draft forward to 12 August, because the mémoire is
due end of month and I want your feedback with time to act on it. That compresses
everything by about nine days — experiments now freeze around the 5th or 6th
rather than the 9th. Which is an argument for dropping the third embedding model
rather than adding it."

**Ask him here:** can we fix a draft review slot shortly after 12 August?

---

## Slide 12 — Decisions

**Say:** "Four things from you. First, review coverage — is a panel of practising
professionals enough, or do you want a domain expert, and could you spot-check ten
records yourself? Second, scope — I'm proposing English-only and no third
embedding model. Third, approve hybrid top-20 plus local reranking as the
architecture. Fourth, a draft review date after 12 August."

**Close with:** "The priority now isn't another model variant. It's freezing
credible gold data and getting to end-to-end grounded answers."

---

# Part 3 — The four hard questions

**"Your gold data is AI-generated. Why should I believe any of these numbers?"**

You shouldn't yet, and I don't present them as final — every figure in this deck
is watermarked as candidate. That's precisely why the validity gate exists, why
it's independent of me, and why I report agreement rather than asserting it. ARES
is the published precedent for exactly this design: synthetic evaluation data made
trustworthy by a human-anchored correction with its uncertainty reported.

**"Isn't the three-system comparison unfair?"**

Yes, and I say so in the mémoire. They don't share a base model, so it's an
end-to-end system comparison, not a causal claim about architectures. That's why
it's demoted to a baseline and the contribution moved to the escalation policy.

**"Why should anyone care about this?"**

Magesh et al. audited commercial RAG legal research tools in 2025 and found they
still hallucinate between 17 and 33 per cent of the time, including miscited
authority. Retrieval grounding is not a safety property. The question of when such
a system should stop and defer to a human is unsolved and consequential — and in
aviation regulation, getting an obligation right while citing the wrong provision
is a real failure mode, not a cosmetic one.

**"Is this deployable?"**

Not yet, and it shouldn't claim to be. It's a decision-support research prototype.
Every output requires verification by a qualified person, that constraint is in the
user-facing output, and it's tested as a safety property rather than left as a
disclaimer.

---

# Part 4 — Before you walk in

- Reread Chapter 2 §2.4 and §2.7 — those are where he's most likely to probe
- Have the justification table in Part 1 printed
- Know your three residuals cold: QA_0063 ambiguous, QA_0080 gold incomplete, QA_0176 real failure
- Never say "63% accurate". Say "63 under a loose proxy, 43 under exact citation plus content"
- Volunteer the RRF limitation before he finds it
- Leave with: a review-coverage decision, a scope decision, and a date after 12 August
