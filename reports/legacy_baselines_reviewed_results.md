# Few-shot, RAG and LoRA re-scored on the frozen benchmark

Status: complete, reproducible. No model was called — the stored predictions in
`Documents/results_*.json` were read as produced. Only the labels and the scorer
changed.

Artifacts: `experiments/legacy_baselines_reviewed_v1/` (`per_record.csv`,
`baseline_metrics.json`, `manifest.json` with input and output hashes).
Entry point: `scripts/rescore_legacy_baselines.py`. Scoring logic:
`src/aviation_rag/evaluation/citations.py`, 29 tests in `tests/test_citations.py`.

---

## 1. What was wrong with the original scorer

The original `citation_match` returned **1.0 whenever the gold citation string
occurred anywhere in the prediction**, and **0.5 for naming the right article
number alone**. A record counted as CORRECT at `citation ≥ 0.5` together with
ROUGE-L ≥ 0.15.

Two consequences, both material:

- **Substring containment leaks downward.** Gold `Article 4` scores a full hit
  inside a prediction that says `Article 4(6)`. Gold `Section 1` scores inside
  `section 1.2`.
- **Half credit for the article number passes the threshold.** A prediction
  citing `Article 16(1)` where the provision is `Article 16(6)` was counted
  correct. In citation-grounded legal QA that is not a near miss; it is the
  wrong provision, and it is precisely the failure the system exists to avoid.

Both behaviours are pinned by tests (`test_legacy_scorer_gets_both_of_those_wrong`)
so the change is auditable rather than asserted.

---

## 2. What replaced it

Two defined measures, reported together, plus the original for continuity.

| Measure | Definition | Undefined when |
|---|---|---|
| `parent` | The prediction names a citation that resolves, **against the parent corpus**, to the provision the gold citation denotes. Only parent identifiers that exist in the corpus can be credited. | the gold citation resolves to no provision |
| `exact` | Every atomic unit of the gold citation, **including the sub-paragraph**, is named in the prediction. `Article 4` does not satisfy `Article 4(6)`, and vice versa. | the gold citation cannot be parsed |
| `legacy` | The original scorer, reproduced verbatim. **Reported for continuity only. Never describe it as accuracy.** | — |

Where a gold citation does not say which regulation it means, every regulation
that has that provision counts as a candidate. The benchmark's own label does
not make the distinction, so a prediction is not penalised for reproducing it.

---

## 3. Scope: 73 records, and why not 98

| | count |
|---|---|
| Frozen benchmark | 98 |
| Excluded by the review (absent from the frozen set) | 2 — QA_0003, QA_0063 |
| Question reworded, so the stored prediction answers a different question | 25 |
| **Comparable** | **73** |
| Of those, with a gold citation that resolves to a provision | 63 |

The 25 break into 8 reworded during the independent review and **17 reworded
earlier by the AI audit** (D010). Both groups are dropped for the same reason:
re-scoring them would compare an answer against a question that was never put to
the model.

**Disclose this selection effect.** The audit rewrote questions it judged vague
or compound — for example `What is the scope of Regulation (EU) No 376/2014?`
became `How does Regulation (EU) No 376/2014 interact with rules on access to
documents and personal-data protection?`. The 73 that remain are therefore
plausibly the *better-posed* questions, and the baselines may score higher on
them than they would on the full frozen set. A clean n=98 comparison would
require re-running generation on the frozen wording, which is blocked pending
the hosted-generation authorisation. Say so rather than presenting 73 as if it
were a random sample.

---

## 4. Results

All 73 comparable records. `parent` and `exact` are over the 63 with a
resolvable gold citation; `legacy` and `rouge` over all 73.

| System / variant | legacy (loose) | parent | exact | grounded | ROUGE-L | retrieval |
|---|---|---|---|---|---|---|
| few-shot k=1 | 0.192 | 0.270 | 0.111 | 0.222 | 0.254 | — |
| few-shot k=5 | 0.205 | 0.254 | 0.095 | 0.238 | 0.259 | — |
| few-shot k=10 | 0.260 | 0.302 | **0.064** | 0.302 | 0.264 | — |
| LoRA 3B | 0.178 | 0.238 | 0.111 | 0.206 | 0.277 | — |
| RAG k=1 | 0.466 | 0.492 | 0.397 | 0.492 | 0.370 | 0.548 |
| RAG k=3 | 0.616 | 0.667 | 0.508 | 0.667 | 0.439 | 0.753 |
| RAG k=5 | **0.671** | **0.730** | **0.508** | 0.730 | 0.467 | **0.890** |

`grounded` = parent-correct **and** ROUGE-L ≥ 0.15. `retrieval` = at least one
retrieved chunk maps, through the stored lineage, to an acceptable parent.

Held-out split only (n=45, of which 36 have a resolvable gold citation):

| System / variant | legacy | parent | exact |
|---|---|---|---|
| few-shot k=10 | 0.178 | 0.222 | 0.028 |
| LoRA 3B | 0.178 | 0.222 | 0.111 |
| RAG k=5 | 0.578 | 0.639 | 0.417 |

---

## 5. What changed, and what did not

**The ranking is unchanged.** RAG beats few-shot beats LoRA under every measure,
on both splits. The original conclusion survives the corrected evaluator. Say
this first — it is the honest headline, and it protects the rest of the thesis.

**The magnitude does not survive.** The loose proxy overstates most where the
failure mode is a plausible-looking wrong citation:

| System | loose | exact | overstatement |
|---|---|---|---|
| few-shot k=10 | 0.260 | 0.064 | **4.1×** |
| LoRA 3B | 0.178 | 0.111 | 1.6× |
| RAG k=5 | 0.671 | 0.508 | 1.3× |

Few-shot is flattered most because its dominant failure was the hallucinated
citation that names a real article. Fifteen of its records counted correct by the
old scorer name the wrong sub-paragraph of the right article:

| Record | gold | predicted |
|---|---|---|
| QA_0057 | Article 18(2) | Article 18(5) |
| QA_0052 | Article 16(6) | Article 16(1) |
| QA_0016 | Article 4(4) | Article 4(1) |
| QA_0174 | Article 16(12) | Article 16(1) |

RAG's fifteen equivalents are the same shape — `Article 4(6)` offered for
`Article 4(4)`, `Article 7` offered for `Article 7(4)`.

**This is the empirical case for the whole project.** A system can retrieve the
right article (RAG parent-level 0.730), write a fluent answer, and still cite the
wrong paragraph. The gap between `parent` 0.730 and `exact` 0.508 on RAG k=5 is
22 points of exactly that failure — and it is invisible to any metric that scores
citations by substring.

---

## 6. A second measurement of the citation-legibility defect

Independently of any system, the benchmark's own citation labels were resolved
against the corpus. Of the 98 frozen records:

| | count |
|---|---|
| The gold citation identifies the parent that holds its evidence | 48 |
| The citation names an Article while the evidence sits in a **GM section** | 28 |
| The citation **omits which of the four regulations** it means | 12 |
| The citation cannot be parsed into any provision | 10 |

**22 of 98 records carry a citation label that cannot be resolved to one
provision from the string alone** — for instance a bare `Article 2`, which exists
in all four regulations in the corpus, or `GM to Reg. (EU) No 376/2014 [04]`.

This is the same defect the reviewers reported in six free-text comments
(*"GM 3.1 = ?"*, *"qu'entends-tu par 'section 2.2'?"*), now measured rather than
anecdotal, and roughly four times larger than the comments alone suggested. Every
one of these citations resolves correctly *inside* the pipeline, because the
pipeline carries the parent identifier alongside. It is only unreadable to a human
holding the citation string — which is the only thing a practitioner is given.

The 28 GM records are a separate and legitimate phenomenon, not an error: the
citation points to the law, the evidence sits in the guidance material discussing
it. It should still be stated, because it means "cited correctly" and "retrieved
the evidence" are different questions on nearly a third of the benchmark.

---

## 7. Caveats to carry into Chapter 5

1. **ROUGE-L is a lexical proxy, not a measure of support.** It is reported
   because the original evaluation used it and continuity matters. Do not call a
   ROUGE threshold "correct content".
2. **n=73, non-randomly selected** (§3). State the direction of the likely bias.
3. **`parent` and `exact` are undefined for 10 of the 73**, excluded from those
   denominators rather than scored zero. Scoring an unreadable label as a failure
   would blame the system for a defect in the benchmark.
4. **LoRA was measured once**, at one variant, and is a 3B model against hosted
   models of unknown but larger size. It is not a controlled comparison and
   should not be presented as one.
