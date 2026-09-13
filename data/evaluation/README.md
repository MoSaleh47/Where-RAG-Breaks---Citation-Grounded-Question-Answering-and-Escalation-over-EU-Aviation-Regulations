# Evaluation Data

Three evaluation views are maintained and must not be conflated.

## Legacy-100

The exact QA IDs used by the stored few-shot, RAG, and LoRA experiments. This view supports continuity only and retains known synthetic-data and leakage limitations.

## Candidate-99

The AI-assisted evidence-linked candidate contains 99 retained questions after 21 corrections and one exclusion. It uses a deterministic legal-parent grouped split of 42 development and 57 test records with zero parent leakage. It supports architecture development, not final claims.

## Reviewed gold

The reviewed gold view does not exist yet. Final records must retain stable question IDs, language, grouped split, canonical parent/child evidence, alternative acceptable evidence sets, citations, reference answers, validation provenance, and reviewer notes.

## Current validity workflow - 25 July 2026

The bounded queue in `independent_review_v1/review_queue.csv` contains 33 records: every AI-audit exception, all three hybrid top-20 residuals, and a deterministic stratified unchanged sample. The repository queue is currently **0/33 decided**.

D023/D024 replace single-reviewer certification with a bilingual multi-reviewer panel and a pre-registered aggregation rule. Collection and aggregation tooling is in `../../review_kit/`. External form responses are not repository evidence until exported, aggregated, adjudicated, and written back to the queue.

After review completion, run `scripts/freeze_reviewed_benchmark.py`. It will:

- require the exact 33 IDs and matching source hashes;
- reject incomplete or inconsistent decisions;
- apply supported corrections and alternative evidence sets;
- preserve panel and author-adjudication provenance;
- exclude rejected records transparently;
- regenerate legal-parent grouped splits if parent assignments changed;
- verify zero source-group leakage;
- write a frozen manifest with SHA-256 lineage;
- refuse to overwrite an existing non-empty output.

Candidate rankings are never converted silently into gold labels. No final accuracy or RAG-ceiling claim is permitted before the frozen reviewed view exists.
