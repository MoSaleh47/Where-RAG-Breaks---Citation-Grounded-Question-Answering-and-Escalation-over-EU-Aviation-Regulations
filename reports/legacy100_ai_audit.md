# Legacy-100 AI-Assisted Evidence Audit

**Audit date:** 18 July 2026  
**Input:** The 100 QA IDs shared by the stored few-shot, RAG, and LoRA results  
**Status:** Candidate benchmark; independent human review is not complete.

## Outcome

| Decision | Count |
|---|---:|
| Retained provisionally without text changes | 78 |
| Rewritten and linked to exact evidence | 21 |
| Excluded as invalid | 1 |
| Total | 100 |

The retained candidate contains 99 questions. Every retained record has a document-qualified parent ID and one or more exact E1 child evidence IDs.

## Why 21 records were rewritten

The audit compared each question, reference answer, stored citation, parent source, and candidate child evidence. It did not infer support from token similarity alone.

Observed defects included:

- a question that attributed Article 3 of Regulation 376/2014 to Regulation 2018/1139;
- citations that named only one paragraph although the answer used two;
- four guidance citations whose section number did not match the source parent;
- answers that converted a reportable occurrence into a legal prohibition;
- answers that invented consequences of non-compliance;
- negative questions that inferred exclusions not stated in the source;
- looser exception language than the regulation actually uses;
- speculative causal links between separate obligations.

The corrected records preserve the original QA IDs for traceability but set source_record_changed to true. Original historical data and predictions remain untouched.

## Excluded record

QA_0003 was generated from concatenated table-of-contents text. Its answer simply refers the reader to Section 2.2 instead of answering from regulatory evidence. It is excluded from the candidate benchmark but remains in the immutable historical N=100 result view.

## Reproducible artifacts

The directory data/evaluation/legacy100_ai_audited_v1 contains:

- legacy100_ai_audited.jsonl: all 100 dispositions and 99 evidence-linked retained records;
- exceptions_for_independent_review.csv: the one exclusion and 21 corrected records;
- audit_summary.json: hashes, counts, and final status.

The corrections are versioned in data/evaluation/legacy100_ai_audit_overrides.csv rather than silently applied to the original QA JSON.

## Candidate split

The 99 retained records are split by parent ID:

| Split | Questions | Legal parent groups |
|---|---:|---:|
| Development | 42 | 12 |
| Test | 57 | 48 |

No parent appears in both splits. The split is deterministic under seed aviation-rag-legacy100-v1.

## Limitations

This is an AI-assisted primary audit. It is stronger than the original unchecked synthetic set because every retained record has explicit evidence and all detected unsupported claims were rewritten or excluded. It is not a substitute for independent human or domain-expert validation.

Before these records support final m?moire claims:

1. independently review all 22 exception records;
2. review a stratified sample of unchanged records across ARTICLE, ANNEX, GM, question type, difficulty, and retrieval outcome;
3. record agreement and any corrections;
4. freeze a new manifest and never tune on its test partition.
