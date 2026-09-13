# Experiment Runs

Experiment directories are immutable evidence. Completed candidate results remain explicitly review-pending until the benchmark is frozen.

## Current inventory - 25 July 2026

| Directory | State | Purpose |
|---|---|---|
| `BM25_local_candidate_v1` | Complete candidate | Lexical baseline |
| `E1_dense_3small_candidate_v1` | Complete candidate | Parent-child + small dense model |
| `E2_dense_3large_candidate_v1` | Complete candidate | Embedding-model ablation |
| `E3_hybrid_rrf_candidate_v1` | Complete candidate | BM25 + large dense equal-weight RRF |
| `E4_cross_encoder_rerank_candidate_v1` | Complete candidate | Local reranking of fixed top-20 pool |
| `E5_context_top5_candidate_v1` | Context complete | Compact top-5 preparation; no generation |
| `E5_context_top5_neighbors_candidate_v1` | Context complete | Top-5 plus neighbours; no generation |
| `cache/embeddings/...` | Complete cache | Small/large corpus and query vectors |
| `cache/rerankers/...` | Complete cache | 1,980 MiniLM pair scores |

The exact completion timestamps, hashes, model revisions, selected pipeline, and blockers are indexed in `../configs/experiment_matrix.yaml`.

## Rules for future runs

New directories should use:

```text
YYYYMMDD_HHMM_<experiment-id>_<short-description>/
```

A full end-to-end run should contain:

```text
config.yaml
manifest.json
environment.txt
notes.md
metrics.json
predictions.jsonl
retrieval_rankings.jsonl
artifacts/
outputs/
```

Earlier candidate directories predate that complete layout; their existing manifests and output hashes are the provenance record and must not be rewritten. Corrected runs receive a new directory and identify the superseded run.
