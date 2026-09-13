# Configurations

`experiment_matrix.yaml` is the live experiment registry. It records the evidence-backed status of E0-E6, the selected candidate pipeline, deterministic split/review seeds, implemented metric keys, review state, and execution blockers.

`generation_evaluation_v1.yaml` is the pre-run contract for E5 answer generation and verification. It remains blocked while the reviewed benchmark is unfrozen, the generator is unselected, and hosted generation is unauthorized.

## Current state - 25 July 2026

- E0 is historical continuity evidence.
- E1-E4 have completed candidate runs and remain review-pending.
- E5 context assembly is complete for two variants; no answer generation has run.
- E6 is optional and has not started.
- The repository review queue is 0/33 decided; external form responses are not synchronized automatically.

## Configuration rules

Every new run must copy its configuration into the immutable run directory and record:

- experiment ID and parent experiment;
- deterministic seed or explicit statement that no seed applies;
- corpus and evaluation manifest paths and hashes;
- chunking, retrieval, fusion, reranking, context, generation, and verification parameters;
- requested metrics;
- model identifiers, revisions, API request IDs, token usage, latency, and cost where applicable.

The candidate runs created before this convention are indexed by the matrix and retain their parameters in `manifest.json`; their directories must not be retroactively rewritten to simulate compliance. Never edit a run configuration after execution starts. Create a new experiment ID for a corrected or materially different run.
