# Generated Artifacts Log

Every artifact produced with AI assistance during the PFE, what it is, where it
lives, and what still needs human work before it can be used. Append-only, in the
same spirit as `decision_log.md`.

This file is the source of truth for the AI-use disclosure in Appendix B. If an
artifact is not listed here, it should not appear in the mémoire.

**Status vocabulary**

| Status | Meaning |
|---|---|
| `installed` | Written into the repository and in use |
| `superseded` | Replaced by a later version; retained for provenance |
| `pending-author-edit` | In the repository but requires the author's own edits before submission |
| `delivered-only` | Produced but not written into the repository |

---

## 2026-07-25 — Benchmark review collection

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `build_review_form.gs` | `review_kit/` | Google Apps Script that generates the bilingual FR/EN review form and its response Sheet from the 33 queued records. Resumable across Apps Script's 6-minute execution limit. | `installed` |
| `aggregate_reviews.py` | `review_kit/` | Aggregates multi-reviewer form responses into vote tallies, inter-rater agreement (Cohen's / Fleiss' κ), and a pre-filled `review_queue.csv` matching the contract in `src/aviation_rag/evaluation/review.py`. | `installed` |
| `REVIEW_PROTOCOL_D023.md` | `review_kit/` | Pre-registered aggregation rule and the reporting requirements that follow from it. | `installed` |
| `README.md` | `review_kit/` | Operating instructions for the kit. | `installed` |
| D023 / D024 entries | `docs/decision_log.md` | Register the multi-reviewer panel and the rule that contested records are author-adjudicated and reported separately. | `installed` |

**Verification performed.** `build_review_form.gs` parses under `node --check`; all
33 records embedded. `aggregate_reviews.py` was round-tripped against synthetic
responses in both form layouts (3 reviewers, partial completion, skips, ties,
disagreement); every auto-decided row validated against the real
`ALLOWED_DECISIONS` / `CHECK_FIELDS` contract imported from `review.py` — 0 errors.

**Live artifacts** (outside the repository, on the author's Google account):

- Review form: `https://docs.google.com/forms/d/e/1FAIpQLScFFuI50LMw-tqNuSFEw1B2OgRSd6BzKAbizMz_ykuDSamtcQ/viewform`
- Response sheet: `https://docs.google.com/spreadsheets/d/1lTMdV5czRXAu-72XOIOKkxO4UBof907Tk3IKYyqqV9k/edit`

---

## 2026-07-25 — Mémoire Chapter 2 and bibliography

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `references.bib` | `memoire/latex/` | Bibliography expanded from 10 to 64 entries (42 conference, 19 journal, 3 legal/institutional). | `installed` |
| `references_pre_expansion_2026-07-23.bib` | `memoire/latex/` | The 10-entry bibliography as it stood before expansion. | `superseded` |
| `02_state_of_art.tex` | `memoire/latex/chapters/` | State of the Art expanded from roughly 4 to 14 typeset pages; five new sections and two summary tables. | `pending-author-edit` |
| `02_state_of_art_pre_expansion_2026-07-23.tex` | `memoire/latex/chapters/` | Previous version of the chapter. | `superseded` |

**Verification performed.** Every one of the 64 bibliography entries was checked
against a primary record (ACL Anthology, PMLR, NeurIPS Proceedings, ACM Digital
Library, JSTOR, EUR-Lex, EASA, or the publisher of record) before inclusion; no
entry was written from memory. The chapter compiles with zero LaTeX errors and
zero undefined references, and all 64 citation keys resolve under BibTeX.

**Outstanding author work before submission.**

1. Replace the draft note at the top of the chapter with the author's own.
2. Section~\ref{sec:sota-legal} states, of a benchmark for citation-bearing QA over
   Regulation (EU) No 376/2014, that none exists "to the author's knowledge".
   Confirm this belief independently before submitting it.
3. Read the chapter in full and rewrite in the author's own voice. The draft was
   AI-produced from verified sources and follows the existing chapter's register,
   but it is not yet the author's writing.

**Known caveats carried from source verification.**

- `gao2023ragsurvey` is an arXiv preprint with no peer-reviewed venue; cited for
  framing only, never as empirical support.
- `bohnet2022attributed` and `kadavath2022know` are preprints.
- `eu2014reg376` gives the Official Journal start page only; the end page was not
  independently confirmed and is deliberately omitted.
- `huang2025hallucination` omits the ACM article number, which was not confirmed.

---

## 2026-07-25 — Mémoire Chapter 4

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `04_methodology.tex` | `memoire/latex/chapters/` | Methodology expanded from roughly 8 to 18 typeset pages. New sections: research design principles, source provenance, deterministic validation, multi-reviewer validation protocol, escalation calibration, statistical treatment, threats to validity, ethics. | `pending-author-edit` |
| `04_methodology_pre_expansion_2026-07-23.tex` | `memoire/latex/chapters/` | Previous version of the chapter. | `superseded` |

**Verification performed.** Every quantity was extracted from a stored manifest,
validation record, or experiment output rather than from prose, and values that
appear only in a written report are attributed to that report in the text.
Compiles with zero LaTeX errors, zero undefined references, zero overfull boxes;
all 30 citation keys resolve.

**Discrepancies found during extraction, recorded as draft notes in the chapter
for the author to resolve:**

1. `configs/experiment_matrix.yaml` still marks E1 as `next` and E2–E4 as
   `pending`/`optional`, though all four have completed runs dated 20–22 July 2026.
   E3's `embedding_model: selected_after_E2` was resolved by D014 but never updated.
2. The metric names declared in that configuration (`child_recall_at_k`,
   `mrr_at_10`, `ndcg_at_10`) do not exist in any metrics file. The implemented
   keys are `any_gold_child_recall`, `mean_evidence_recall`, `mrr`, `ndcg`,
   `parent_recall`, `n`.
3. `random_seed: 42` is declared but unused — splitting takes a *string* seed
   consumed by SHA-256, not an RNG.
4. `source_manifest.csv` records the primary corpus as `version = 2022-12` while
   the build manifest and corpus audit describe a 2023-09-27 export. Both are
   correct (December 2022 revision, exported September 2023); state both.
5. `E1_corpus_audit.md` reports 87 short units and 8 long units; these counts are
   report-only and absent from `validation.json`.
6. `validation.json` records `ignored_block_count: 173` with no documentation
   anywhere of what an ignored block is.
7. `answer_output_v1.schema.json` does not enforce prompt rule 11
   (`abstain=false` implies null reason), and the enum value `verification_failed`
   is never produced by any prompt rule.
8. `scripts/README.md` numbering runs 1–11, then 13, then 12.

**Outstanding author work.** Replace the two draft notes that are mine with your
own wording; resolve the eight discrepancies above; read and rewrite in your voice.

---

## 2026-07-25 - Configuration and progress reconciliation

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| Experiment registry v2 | `configs/experiment_matrix.yaml` | Reconciles E0-E6 with stored manifests, D014/D015/D018 selections, deterministic string seeds, actual metric keys, review status, and generation blockers. | `installed` |
| Generation protocol status | `configs/generation_evaluation_v1.yaml` | Distinguishes completed E5 context preparation from generation that has not run and is not authorized. | `installed` |
| Project status documentation | `README.md` and scoped READMEs | Replaces stale E1-next and single-reviewer descriptions with the 25 July repository state. | `installed` |
| Meeting and mémoire status updates | `reports/supervisor_meeting_29_july_2026.md`, `memoire/00_table_of_contents.md`, `memoire/latex/chapters/04_methodology.tex` | Aligns reusable writing with D023/D024 and the stored experiment record. | `pending-author-edit` |

**Verification performed.** Completion timestamps, model names, revisions, parameters, hashes, split counts, seed strings, metric keys, context statistics, and blocker states were read from the stored manifests/configuration rather than inferred from prose. The repository review queue was re-counted as 0/33 decided. The three experiment-matrix discrepancy notes in Chapter 4 were replaced with reconciled factual statements.

**Discrepancies resolved from the earlier Chapter 4 audit.** Items 1-3 are resolved: experiment statuses/model selection, actual deterministic seeds, and metric-key names. The scripts README numbering issue is also corrected. Corpus-version wording, ignored-block documentation, schema/prompt alignment, and author rewriting remain separate outstanding work.

## 2026-07-25 — Independent verification of the reconciliation

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| Typesetting fix | `memoire/latex/chapters/04_methodology.tex` | The reconciled seeds paragraph introduced an overfull line (35.8 pt); the two seed strings were moved into a list so the paragraph breaks cleanly. | `installed` |
| Log ordering | `docs/generated_artifacts_log.md` | The reconciliation entry had been appended below the template block; entries are now chronological with the template last. | `installed` |

**Verification performed.** The reconciliation was checked against the repository
rather than accepted from its summary:

- all five run completion timestamps in `experiment_matrix.yaml` match their
  manifests exactly (E1 09:32:16, E2 09:34:28, E3 09:40:09 on 20 July; E4
  07:44:48 on 22 July; BM25 21:15:29 on 18 July);
- E2 embedding dimensions (3072) and the reranker commit hash match the manifests;
- the review queue was independently re-counted: 33 rows, 0 decided;
- D023 and D024 are present and unaltered in the decision log;
- `scripts/README.md` numbering now runs 1–13 in order;
- both YAML files parse;
- the earlier sections of this log are preserved verbatim;
- `build_review_form.gs` and `aggregate_reviews.py` were not modified (only the
  kit README was), so the verification recorded for them still holds;
- Chapter 4 was diffed line by line: exactly three draft notes were replaced with
  reconciled prose and nothing else changed. It recompiles with zero errors, zero
  undefined references, and — after the fix above — zero overfull lines.

**Not independently confirmed.** The reconciliation reports 70 passing tests. The
suite contains 61 `test_` functions across 11 files, which is consistent with 70
collected cases once parametrisation is expanded, but pytest was not run here.

---
## 2026-07-27 — Mémoire Chapters 1 and 3, and the review cutoff decision

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `01_introduction.tex` | `memoire/latex/chapters/` | Introduction expanded from ~4 to ~7 typeset pages. New: methodological stance, expanded scope and delimitations, the three-residuals finding stated as the motivating observation. | `pending-author-edit` |
| `03_project_context.tex` | `memoire/latex/chapters/` | Project context expanded from ~4 to ~8 typeset pages. New: the regulatory domain section, intended users, data provenance, governance, revised schedule, risk table. | `pending-author-edit` |
| `01_introduction_pre_expansion_2026-07-23.tex`, `03_project_context_pre_expansion_2026-07-23.tex` | `memoire/latex/_superseded/` | Previous versions. | `superseded` |
| D025 | `docs/decision_log.md` | Fixes the review collection cutoff at 6 August and pre-registers freezing on whatever coverage exists at that date. | `installed` |
| `_superseded/` | `memoire/latex/` | All pre-expansion backups moved out of `chapters/`, where they duplicated live chapter labels. | `installed` |

**Verification performed.** Both chapters compile with zero LaTeX errors, zero
undefined references, and zero overfull boxes. The regulatory-domain section of
Chapter 3 was written from this project's own validated corpus — instrument
composition, article titles and annex titles were read from
`data/processed/E1_parent_child_v1/parents.jsonl`, not from external summaries —
because the EUR-Lex summary page could not be retrieved to a standard that would
justify quoting provisions. **No specific provision (deadline, addressee,
threshold) is asserted anywhere in the chapter.**

**Outstanding author work.**

1. Section 3.1 (host organisation) is a stub: company name, department, team,
   industry-supervisor details, confidentiality confirmation. Nothing else in the
   chapter depends on it.
2. A draft note in Chapter 3 asks for one worked example — a question, the
   provision answering it, and the neighbouring provision qualifying it. The
   material is in the processed corpus.
3. Both chapters need reading and rewriting in the author's own voice.

---

## 2026-08-08 — Benchmark adjudication and freeze

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `review_queue.csv` | `data/evaluation/independent_review_v1/` | Completed review queue: 14 panel-cleared rows aggregated from the form responses, 19 rows adjudicated by the author, three rows repaired under D026. | `installed` |
| `review_queue_pre_adjudication_2026-07-23.csv` | `data/evaluation/independent_review_v1/` | The empty queue as generated on 23 July, before any decision was entered. | `superseded` |
| `review_queue_as_exported_2026-08-08.csv` | `review_kit/out_final/` | The author's export from `adjudicate.html`, before the three D026 repairs. Retained so the repairs are auditable. | `superseded` |
| `reviewed_benchmark_v1/` | `data/evaluation/` | Frozen benchmark: `reviewed_benchmark.jsonl` (98 records), `split_manifest.csv`, `freeze_summary.json`, `manifest.json` with input and output SHA-256 hashes, and a copy of the decisions CSV. | `installed` |
| D026, D027 | `docs/decision_log.md` | Register the three adjudication repairs and the freeze. | `installed` |
| `adjudicate.html` | `review_kit/` | Offline single-file adjudication tool with live validation against the freeze contract; used to produce the 19 author decisions. | `installed` |

**Verification performed.** The completed queue was validated against
`validate_review_rows` imported from `src/aviation_rag/evaluation/review.py` — 33
rows, 30 columns, zero contract errors, every row carrying a non-empty
justification as D024 requires. `apply_review_decisions` was dry-run before the
freeze and its summary matched the freeze output exactly. After the freeze,
`split_manifest.csv` was checked independently: no legal parent appears in both
splits, 98 records over 60 parents, 40 development / 58 test. No record in the
frozen set has acceptable evidence spanning more than one legal parent, so the
D005 argument against agentic retrieval still holds on the reviewed benchmark.

**Author decisions recorded here for transparency.** The 19 contested records
were decided by the author, not by AI. The three repairs under D026 were proposed
by AI after contract verification and approved by the author before application;
the pre-repair export is retained alongside.

**Outstanding author work.**

1. QA_0071 now carries 22 gold children as a single conjunctive evidence set.
   This is the hardest record in the benchmark by construction and will likely
   score zero evidence recall. Decide whether to report it as a genuine hard case
   or to relax it to `accept_with_alternative_evidence` before the results
   chapter is written — and say which, explicitly, in Chapter 5.
2. QA_0097 was accepted against a reviewer's objection that Regulation (EU)
   2020/2034 is not cited in 376/2014. The justification is in `review_notes`;
   confirm it survives a second reading before the mémoire relies on the record.
3. The frozen split (40/58) differs from the earlier candidate split (42/57).
   Every figure computed on the old partition is now stale and must be
   regenerated, not carried over.

---

## 2026-08-08 — Split preservation and reviewed-label retrieval

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `freeze_reviewed_benchmark.py` | `scripts/` | Gains `--inherit-splits`: carries an existing development/test assignment over to the frozen benchmark and refuses any retained record that has none. Records `split_provenance` and the source manifest hash in `freeze_summary.json`. | `installed` |
| `_superseded_freeze_reviewed_benchmark_2026-08-08.py` | `scripts/` | The freeze script as it stood before the patch. | `superseded` |
| `reviewed_benchmark_v1/` | `data/evaluation/` | Re-frozen with the inherited split: 98 records, 42 development / 56 test, 60 parents, zero leakage. | `installed` |
| `_superseded_reviewed_benchmark_v1_recomputed_split_2026-08-08/` | `data/evaluation/` | The first freeze, with the recomputed split that moved 12 records. Retained so D028 is auditable. | `superseded` |
| `BM25_local_reviewed_v1/` | `experiments/` | BM25 re-scored against reviewed labels on the inherited split. Local, no API calls. | `installed` |
| `rerun_reviewed_retrieval.py` | `scripts/` | Driver for the remaining stages: dense (3-small, 3-large), RRF fusion, cross-encoder reranking, report assets. Writes to `*_reviewed_v1` directories and a separate embedding cache so the candidate runs stay reproducible. | `installed`, not yet run |
| D026, D027, D028 | `docs/decision_log.md` | Adjudication repairs, the freeze, and the split-inheritance decision. | `installed` |

**Verification performed.** The recomputed partition was compared record by record
against `legacy100_candidate_splits_v1/split_manifest.csv`: 12 records had changed
side, which is what prompted D028. After re-freezing with `--inherit-splits`, that
comparison returns zero changed records, and parent disjointness was re-checked
independently of the freeze script's own assertion. BM25 on reviewed labels is
therefore a paired comparison against the candidate run — same partition, one
record fewer in test.

**Result of the re-scoring (BM25 only, so far).** Evidence recall improves slightly
on both sides: development `mean_evidence_recall@5` 0.612 → 0.652, test 0.634 →
0.652; `any_gold_child_recall@10` development 0.810 → 0.833, test 0.842 → 0.857.
The review repaired labels rather than exposing new retrieval failures. State the
direction plainly in Chapter 5: reviewed labels did not flatter the system, they
moved it by one to four points.

**Outstanding author work.**

1. Run `python scripts/rerun_reviewed_retrieval.py` from the repository root on a
   Python that has `openai`, `torch` and `transformers` installed. It re-embeds the
   98 questions (about 2,500 tokens per model, authorised under D013) and reruns
   fusion, reranking and the figures.
2. Only after all five systems are re-scored may the `\candidate` markers and the
   review-pending watermarks come off. Do not remove them selectively.
3. Report the development fraction as observed (42/98 = 0.429), not as the 0.400
   requested by the script's default.

---

## 2026-08-08 — Retrieval re-scored on the frozen benchmark

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `BM25_local_reviewed_v1/`, `E1_dense_3small_reviewed_v1/`, `E2_dense_3large_reviewed_v1/`, `E3_hybrid_rrf_reviewed_v1/`, `E4_cross_encoder_rerank_reviewed_v1/` | `experiments/` | All five retrieval systems re-scored against frozen reviewed labels on the inherited 42/56 split. Each carries its own manifest with input and output hashes. | `installed` |
| `reviewed_v1/` | `reports/assets/` | Figure, SVG and CSV built from the reviewed metrics, without the candidate watermark. | `installed` |
| `_superseded_mislabelled_2026-08-08/` | `reports/assets/reviewed_v1/` | The first build of these assets, which carried the candidate watermark and title over reviewed data. Retained, not deleted, because it was briefly on disk. | `superseded` |
| `build_candidate_report_assets.py` | `scripts/` | Gains `--reviewed`; two hard-coded strings replaced by derived values (D029). | `installed` |
| `rerun_reviewed_retrieval.py` | `scripts/` | Rewritten: resumes from completed stages, checks every dependency before running anything, supports `--python`, `--only` and `--list`. Fixed a defect in the first version that passed a directory where `--score-cache` requires a file, which would have failed stage 5 after the paid embedding stages had already run. | `installed` |
| D029, D030 | `docs/decision_log.md` | Watermark policy, and the disclosure that D014's evidence weakened. | `installed` |

**Verification performed.** All five candidate/reviewed pairs were compared metric
by metric on both splits. The reviewed figure was rendered and read back to confirm
the watermark is gone, the axis label no longer says "Candidate", and the ceiling
annotation reads 54/56 rather than the literal 54/57 it previously contained.
Rebuilding the candidate assets from the patched script reproduces a byte-identical
CSV. D014 was re-checked on reviewed development data and the one reversal is
recorded in D030 rather than being quietly dropped.

**Headline result on the frozen benchmark (test, n=56), any-gold-child recall.**

| System | k=1 | k=5 | k=10 | k=20 |
|---|---|---|---|---|
| Hybrid RRF | 0.554 | 0.839 | 0.911 | 0.964 |
| Hybrid + cross-encoder | 0.714 | 0.893 | 0.946 | 0.964 |

Against candidate labels the same system read 0.667 / 0.877 / 0.930 / 0.947. Every
system improved on test: reviewed labels moved results by roughly one to five points
in the system's favour, and the reranker's top-1 gain over hybrid alone is now 16
points rather than 15.8. Mean evidence recall for hybrid + reranker on test is 0.811
at k=5 and 0.856 at k=10.

**Outstanding author work.**

1. The `\candidate` markers in the mémoire can now come off **for retrieval results
   only**. Generation, verification, abstention and the three-system baseline are
   still unmeasured on the frozen benchmark and must keep theirs.
2. Chapter 5 must state the D030 reversal, not just the five criteria that hold.
3. QA_0071 still carries 22 gold children in one conjunctive set and scores 0 at
   k=5 by construction; decide how it is reported before writing the results.

---

## 2026-08-08 — Corrected evaluator and the three-system baseline

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `citations.py` | `src/aviation_rag/evaluation/` | Parses legal citations from free text and resolves them against `parents.jsonl`. Provides parent-level and exact citation matching, plus the original scorer reproduced verbatim for continuity. | `installed` |
| `test_citations.py` | `tests/` | 29 tests: parsing forms taken from the gold citations that actually occur, resolution against the real corpus, and two tests that assert the *old* scorer's errors so the change stays auditable. | `installed` |
| `rescore_legacy_baselines.py` | `scripts/` | Re-scores the stored few-shot / RAG / LoRA predictions on the frozen benchmark. Calls no model; records `model_calls: 0` in its manifest. | `installed` |
| `legacy_baselines_reviewed_v1/` | `experiments/` | `per_record.csv` (511 rows), `baseline_metrics.json`, `manifest.json` with input and output hashes. | `installed` |
| `legacy_baselines_reviewed_results.md` | `reports/` | Written results: what the old scorer counted, what replaced it, the numbers, and the caveats. | `installed` |
| D031, D032, D033 | `docs/decision_log.md` | The corrected evaluator, the n=73 scope, and the citation-legibility measurement. | `installed` |
| `evaluation/__init__.py` | `src/aviation_rag/` | Exports the new citation utilities. | `installed` |

**Verification performed.** The parser was checked against all 80 distinct gold
citation strings in the frozen benchmark, including the awkward forms
(`Article 16(11)-(12)`, `Article 13, paragraphs 4 and 5`, `Articles 20(1)-(2), 10
and 11`, `Article 7(4) and 7(8)`, `Regulation 2015/1018, Annex V`). Two elliptical
forms failed the first implementation and were fixed, not worked around. A
negative case is pinned: `Article 4 and 30 days later` must not yield an
Article 30. Resolution only ever emits parent identifiers that exist in
`parents.jsonl`, so an invented reference resolves to nothing rather than to a
plausible-looking parent. All 29 tests pass. The re-scoring was run in the
container and re-run on the author's machine with identical output.

**Headline result.** The ranking RAG > few-shot > LoRA is unchanged under every
measure on both splits. The magnitude is not: exact citation correctness is
few-shot k=10 0.064 against a loose 0.260, LoRA 0.111 against 0.178, RAG k=5
0.508 against 0.671. RAG reaches 0.730 at parent level, so the 22-point gap to
0.508 is entirely "right article, wrong paragraph".

**Outstanding author work.**

1. Chapter 5 must lead with the unchanged ranking, then the corrected magnitudes.
   Leading with the drop invites the question of whether the earlier chapters can
   be trusted; leading with the ranking answers it.
2. State the n=73 selection effect in the author's own words (D032).
3. `pytest` is not installed in the environment used on the author's machine for
   these runs; the 29 tests were executed in the analysis container. Run
   `python -m pytest tests/` locally once before submission so the test evidence
   is reproducible on the author's own machine.
4. The three-system comparison remains a historical baseline (D001). Do not let
   the corrected numbers turn it back into the contribution.

---

## 2026-08-08 — E5 generation on development, and the verification rule

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `run_generation.py` | `scripts/` | Runs evidence-constrained generation. Defaults to development and refuses the held-out split without an explicit flag; caches every response by model, prompt, schema and context so re-runs cost nothing; builds the API's strict schema from the project schema and re-validates responses locally. | `installed` |
| `E5_context_top5_reviewed_v1/`, `E5_context_top5_neighbors_reviewed_v1/` | `experiments/` | Evidence contexts rebuilt on the frozen benchmark from the reviewed reranked rankings. The candidate contexts were built against pre-review questions. | `installed` |
| `E5_generation_top5_dev_v1/`, `E5_generation_top5_dev_v2/` | `experiments/` | Generated answers with per-record verification, summary and hashed manifest. 42 records each. | `installed` |
| `evidence_constrained_answer_v2.md` | `prompts/` | One rule changed: quote an unbroken run of consecutive words, no ellipsis, no splicing. v1 retained for the comparison. | `installed` |
| `verification.py` | `src/aviation_rag/generation/` | Contiguity-based quote matching with punctuation and typography normalisation; reports the byte-level result alongside; flags elisions explicitly. | `installed` |
| `_superseded_verification_2026-08-08.py` | `src/aviation_rag/generation/` | The previous verifier. | `superseded` |
| `test_answer_verification.py` | `tests/` | Extended from 5 to 9 tests. | `installed` |
| `E5_generation_dev_results.md` | `reports/` | Written results, the ablation, and the two findings. | `installed` |
| D034–D039 | `docs/decision_log.md` | Authorisation, model choice, split discipline, the verbatim rule, prompt v2, and what the results imply. | `installed` |

**Verification performed.** The verifier change was validated by re-running v1
from cache with zero API calls, so the v1-vs-v2 comparison differs only in the
prompt, and the v1 numbers under old and new rules come from identical model
output. Failing spans were classified by graded normalisation to separate
typography from punctuation from genuine mismatch; zero spans were repaired by
typography alone, which is what justified normalising punctuation rather than
unicode. The two surviving v2 failures were read individually against their
sources rather than counted.

**Results.** 0 parse failures, 0 refusals, 0 schema violations across 84 answers.
Grounding on development rises from 32/42 to 40/42 with one prompt rule; marked
elisions fall from 7 answers to zero.

**Two findings, both stronger than the numbers.**

1. v2 removed every marked elision and introduced one unmarked splice (QA_0294),
   which an ellipsis detector would have passed and contiguity matching caught. A
   prompt constraint displaced the failure into a less visible form.
2. The model abstained 0 times in 84 opportunities, including on a fabricated
   prohibition, despite a free and well-formed abstention channel.

**Outstanding author work.**

1. Write both findings into Chapter 5; the abstention one belongs in the
   conclusion as well.
2. Describe v2 as development-set selection, not as an independent result.
3. Do not generate on the held-out split until abstention and escalation
   thresholds are frozen.
4. The neighbour-enriched context variant is built and unrun; comparing it would
   test whether grounding is sensitive to context breadth.

---

## 2026-08-08 — Escalation calibration (negative result)

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `calibrate_escalation.py` | `scripts/` | Evaluates candidate escalation rules against runtime-observable signals. Emits escalation rate, precision, recall and a Wilson interval per rule, plus the sample size needed to separate each precision from the base error rate. Fits nothing. Refuses any split but development without an explicit override. | `installed` |
| `escalation_dev_v1/` | `experiments/` | `signals.csv` (42 records, 13 runtime signals and 2 gold outcomes), `calibration.json`, hashed `manifest.json` with `model_calls: 0`. | `installed` |
| `escalation_calibration_dev.md` | `reports/` | Written result, power analysis and threats. | `installed` |
| D040, D041, D042 | `docs/decision_log.md` | Not fitting a threshold, keeping both verification layers, and gating on quote failure while stating the cost assumption. | `installed` |

**Verification performed.** Every figure in the report is reproduced by the
script into `calibration.json`, so no number in the mémoire will exist only in
prose. A first draft of the report claimed that every rule's confidence interval
contained the base rate; the generated artifact contradicted that -- two rules
have a lower bound of 0.23 against a base rate of 0.214 -- and the report was
corrected rather than the claim retained. Both are still described as
indistinguishable from the base rate, because a two-point margin on nine error
events is not a result, but the correction is the point: the artifact was allowed
to overrule the prose.

**Result.** Base error rate 9/42. Best recall 0.89 at precision 0.42 [0.23, 0.64],
escalating 45% of questions. Failure-mode overlap is exactly zero: 9 evidence
errors, 2 quote failures, no record with both. Demonstrating the observed
precision against the base rate would need roughly 178 questions; the frozen
benchmark has 98.

**Outstanding author work.**

1. Present this as a negative result with a power requirement, not as a
   calibrated policy. It is a stronger contribution than a threshold fitted to
   nine events, and it is the one an examiner cannot dismantle.
2. State the cost assumption whenever an escalation rate appears (D042).
3. Do not run escalation on the held-out split. There is no policy to freeze yet.
4. If the benchmark is ever extended, the power table gives the target directly.

---

## 2026-08-08 — Mémoire Chapter 5 rewritten on frozen results

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `05_results.tex` | `memoire/latex/chapters/` | Results chapter rewritten against the frozen benchmark: corpus and review, retrieval, re-scored baselines, generation and verification, escalation calibration, the two properties no internal metric detects, threats to validity. 8 tables, 1 figure, 17 citations. | `pending-author-edit` |
| `05_results_pre_frozen_2026-08-08.tex` | `memoire/latex/_superseded/` | The previous chapter, written against candidate labels. | `superseded` |
| `reviewed_retrieval_comparison.png` | `memoire/latex/figures/` | The unwatermarked figure from `reports/assets/reviewed_v1/`. | `installed` |

**Candidate markers removed, deliberately and only here.** The previous chapter
opened with a red draft box stating that every percentage was a candidate result
pending review, and its table captions carried "independent review pending". Those
are gone because the condition they described no longer holds: D027 froze the
benchmark and every retrieval and baseline figure in the new chapter is computed
against frozen reviewed labels. The markers were not removed from anything still
unreviewed. In their place the chapter opens with an accurate status box, and the
generation and escalation sections state on every page that they are development
-only and that no answer has been scored on the held-out partition.

**Verification performed.** Every figure in the chapter was read from a stored
metrics file, manifest or calibration artifact, not from an earlier report; the
numbers were extracted in a single pass and transcribed directly into the tables.
A structural check confirms balanced environments, tabular column counts matching
their specifications on every row, all 17 citation keys present in
`references.bib`, and all 21 internal references resolving to a label that exists
somewhere in the six chapters. The chapter was **not** typeset: the analysis
environment's TeX installation lacks `siunitx` and `biber`, so the build must be
run on the author's machine.

**Outstanding author work.**

1. **Build the PDF** (`cd memoire/latex && latexmk -pdf main.tex`) and check for
   overfull boxes and undefined citations. Several keys newly cited here were not
   in the previous `.bbl`, so biber must run.
2. **Read Section 5.2.2 and Section 5.6 particularly closely.** They make the two
   claims the chapter rests on — that reviewer disagreement is a finding, and that
   no escalation threshold is defensible at this sample size. Both must be in the
   author's own voice and the author must be willing to defend them orally.
3. Rewrite the chapter in the author's voice as with Chapters 1–4.
4. Chapter 6 is not yet written and should follow from Section 5.6.4 and the
   abstention result in Section 5.5.5.

---

## Template for future entries

```
## YYYY-MM-DD — <short title>

| Artifact | Path | Purpose | Status |
|---|---|---|---|
|  |  |  |  |

**Verification performed.**

**Outstanding author work.**
```

## 2026-08-27 — Response to the supervisor review

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `fig_pipeline.tex`, `fig_escalation.tex`, `fig_failure_modes.tex` | `memoire/latex/figures/` | The three drawn figures added under D046: the end-to-end pipeline, the escalation ladder with the evidential status of each transition, and a unit chart of the two failure modes over the 42 answered development questions. TikZ, so they compile with the document and depend on no external image. | `installed` |
| `rerun_legacy_baselines.py` | `scripts/` | Regenerates the few-shot and RAG baselines over the frozen question wording so the three-system comparison can cover all 98 records (D049). Historical system prompts verbatim, seed 42, temperature 0, model pinned to a dated snapshot, NumPy cosine in place of faiss. Caches every response by a digest over model and prompts, so it resumes without re-billing; `--dry-run` builds every request and calls nothing. | `installed` |
| `rerun_legacy_lora.py` | `scripts/` | Re-runs the LoRA adapter over the frozen wording, offline and unbilled (D049). Refuses to run if any frozen record is found in the adapter's training split, and reports how many unchanged records reproduce their stored prediction exactly. `--check-only` validates data and environment without loading a model. | `installed` |
| `runbook_supervisor_points_3_and_4.md` | `docs/` | The commands for the two runs that need the API key, in order, with costs, guardrails and what happens to the chapters afterwards. | `installed` |
| `legacy_rerun_frozen98_v1/` | `experiments/` | Regenerated few-shot and RAG predictions over the frozen wording, 588 records, with a manifest recording the pinned model snapshot, digests and USD 0.0860 of billed tokens. | `installed` |
| `legacy_baselines_frozen98_v1/` | `experiments/` | The three systems re-scored on the frozen labels: few-shot and RAG at n=98 (88 resolvable), LoRA at n=73 (63 resolvable) from its stored predictions. Per-record CSV and metrics JSON. | `installed` |
| `E5_generation_neighbors_dev_v2/` | `experiments/` | Enriched-context generation on the 42 development records, comparable line for line with `E5_generation_top5_dev_v2`. | `installed` |

## 2026-09-12 — Code publication

| Artifact | Path | Purpose | Status |
|---|---|---|---|
| `D_code.tex` | `memoire/latex/appendices/` | Appendix D. Four listings sliced programmatically from the real source files at the line ranges named in their captions, so the printed code cannot drift from the repository (D059). | `installed` |
| `.gitignore` (extended) | `aviation_rag_research/` | Excludes `review_kit/_private*/`, any `*PRIVATE*` path and the billing exports, applied before the repository's first commit (D060). | `installed` |
