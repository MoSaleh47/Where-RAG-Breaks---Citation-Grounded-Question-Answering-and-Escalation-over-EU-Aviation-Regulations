# Scripts

Scripts are thin command-line entry points. Reusable logic belongs in `src/aviation_rag/` and must be tested.
Implemented entry points:

1. profile_source_xml.py and inspect_source_range.py for source auditing;
2. build_parent_child_corpus.py for deterministic E1 corpus construction;
3. map_legacy_sources.py for flat-chunk to E1 parent lineage;
4. build_child_evidence_candidates.py for the human evidence-review queue.
5. build_legacy100_ai_audit.py for evidence-linked candidate curation;
6. build_candidate_splits.py for deterministic legal-parent grouped splits;
7. run_bm25_retrieval.py and run_dense_retrieval.py for sparse and dense baselines;
8. run_rrf_fusion.py for equal-weight hybrid candidate generation;
9. run_cross_encoder_reranking.py for local top-20 query-passage reranking;
10. prepare_independent_review.py for the bounded human validity gate;
11. build_candidate_contexts.py for deterministic evidence-context variants.
12. build_candidate_report_assets.py for hashed, review-watermarked retrieval figures and CSV data.
13. freeze_reviewed_benchmark.py for validation, correction application, hashes, and leakage-safe reviewed splits.

All generated outputs record or inherit SHA-256 lineage. Candidate mapping scripts do not silently convert fuzzy matches into gold labels.


Planned entry points:

1. `run_generation.py`
2. `evaluate_predictions.py`
3. `build_report_assets.py`

Each script must accept an explicit configuration path and refuse to overwrite an existing completed experiment directory.

