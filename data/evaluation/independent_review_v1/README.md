# Independent Benchmark Review

## Current protocol - 25 July 2026

D023/D024 supersede the earlier single-reviewer workflow. The preferred validity gate is now a bilingual FR/EN panel of practising aviation professionals, with the aggregation rule fixed before collection.

- Required records: 33.
- Repository decisions completed: 0/33.
- Target: at least two independent ratings per record, aiming for three reviewers.
- Collection and aggregation instructions: `../../../review_kit/README.md`.
- Pre-registered rule: `../../../review_kit/REVIEW_PROTOCOL_D023.md`.
- Exact required IDs and input hashes: `review_requirements.json`.

The repository CSV remains the freeze contract and final adjudication target. External Google Form responses do not update it automatically.

## Why review is required

The same AI-assisted process that proposed benchmark corrections cannot independently certify them. The queue covers all 22 audit exceptions, all three hybrid top-20 residuals, and ten deterministic unchanged controls. Two residuals overlap the exception set, producing 33 unique records.

Reviewers judge:

- whether the question is clear and unambiguous;
- whether every material answer claim is supported;
- whether the canonical citation is correct;
- whether the selected evidence is complete;
- whether equivalent one-child or multi-child evidence routes should count;
- whether the record needs correction, exclusion, or uncertainty marking.

## Workflow

1. Collect ratings through the form created by `review_kit/build_review_form.gs`.
2. Export the response Sheet as CSV.
3. Run `review_kit/aggregate_reviews.py` to produce vote tallies, agreement statistics, and `review_queue_filled.csv`.
4. Author-adjudicate contested or correction-flagged rows under D024 and document the reason.
5. Copy the fully completed result to `data/evaluation/independent_review_v1/review_queue.csv`.
6. Run the freeze command below.

Partial reviewer completion is acceptable, but a record is panel-decided only when it satisfies the pre-registered minimum-rater and majority rules. Inter-rater disagreement must be reported, not hidden.

## Allowed adjudication fields

`reviewer_decision` accepts:

- `accept`;
- `accept_with_alternative_evidence`;
- `correct`;
- `exclude`;
- `uncertain`.

The four check columns accept `yes`, `no`, or `uncertain`. Use semicolon-separated child IDs for one-child alternatives and JSON evidence-set lists for alternatives that require several children together. Corrections must be minimal, evidence-supported, attributed, and dated in ISO format.

## Freeze

From `aviation_rag_research/`:

```powershell
python scripts/freeze_reviewed_benchmark.py --audited-qa data/evaluation/legacy100_ai_audited_v1/legacy100_ai_audited.jsonl --review-csv data/evaluation/independent_review_v1/review_queue.csv --children data/processed/E1_parent_child_v1/children.jsonl --output data/evaluation/reviewed_benchmark_v1
```

The command intentionally refuses incomplete reviews, malformed values, mismatched hashes, missing IDs, and overwrite attempts. Until it succeeds and metrics are regenerated, every retrieval percentage remains a candidate result and final generation stays blocked.
