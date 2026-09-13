# Reports

This directory holds reusable outputs for the supervisor presentation, mémoire, and final defense. Candidate artifacts must identify their producing experiment and evaluation view and must retain the review-pending label.

## Implemented

- `E1_corpus_audit.md`: hierarchy-aware corpus evidence and validation.
- `legacy_to_e1_mapping_audit.md`: historical-to-E1 lineage.
- `legacy100_ai_audit.md`: AI-assisted candidate benchmark audit.
- `BM25_candidate_results.md`: lexical baseline.
- `dense_hybrid_candidate_results.md`: small/large embedding comparison and hybrid RRF.
- `cross_encoder_rerank_candidate_results.md`: local reranking results and negative ablations.
- `assets/retrieval_candidate_v1/`: generated PNG, SVG, metric CSV, and hash manifest with a visible candidate watermark.
- `supervisor_meeting_29_july_2026.md`: reusable ten-slide narrative and speaker notes.

## Still required

- panel-review coverage, agreement, and contested-record tables;
- reviewed retrieval/reranking figures after benchmark freeze;
- end-to-end generation, verification, abstention, latency, token, and cost results;
- switching-policy coverage/risk curve;
- final architecture and failure-routing diagrams;
- an actual PPTX or equivalent presentation artifact. The slide narrative exists, but no presentation file is stored yet.

No candidate watermark may be removed until the repository review queue is complete, the freeze command succeeds, and metrics are regenerated against the reviewed labels.
