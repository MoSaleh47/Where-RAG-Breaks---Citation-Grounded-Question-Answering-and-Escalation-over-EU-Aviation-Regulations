# Aviation RAG Research Workspace

This directory is the clean workspace for the remaining PFE work. Files in the project root and `../Documents/` are treated as the historical baseline and must not be overwritten.

The research objective is to identify where conventional RAG fails in citation-bearing aviation-regulation QA and to evaluate a calibrated escalation path: hierarchy-aware retrieval, hybrid retrieval, reranking, verification, constrained multi-step retrieval, and human review.

The complete project plan is maintained in [`../plan_for_rest_of_pfe.md`](../plan_for_rest_of_pfe.md). The machine-readable experiment status is maintained in [`configs/experiment_matrix.yaml`](configs/experiment_matrix.yaml).

## Working rules

1. Raw source snapshots are immutable.
2. Every run records its parameters, input hashes, outputs, metrics, model identifiers, and status in a manifest.
3. Legacy proxy accuracy, exact citation accuracy, factual correctness, groundedness, and retrieval recall are reported separately.
4. The legacy 100-question sample is kept for continuity; final claims require the reviewed, source-grouped evaluation set.
5. Only one major experimental component changes at a time.
6. Failed and rejected ablations are retained and documented.
7. No credentials, model binaries, generated indexes, or private data belong in the repository.

## Directory map

```text
aviation_rag_research/
|-- app/                 # Evidence-first prototype
|-- configs/             # Experiment registry and generation protocol
|-- data/                # Raw, interim, processed, evaluation, and manifests
|-- docs/                # Protocol, decisions, data dictionary, AI artifact log
|-- experiments/         # Immutable run directories and model-score caches
|-- memoire/             # School-compliant LaTeX report source
|-- prompts/             # Versioned generation prompts
|-- reports/             # Reusable tables, figures, and meeting material
|-- review_kit/          # Multi-reviewer form and aggregation workflow
|-- schemas/             # Structured answer contracts
|-- scripts/             # Reproducible entry points
|-- src/aviation_rag/    # Tested implementation
`-- tests/               # Corpus, retrieval, evaluation, and safety tests
```

## Experiment ladder - status on 25 July 2026

| ID | Intervention | Repository state | Claim status |
|---|---|---|---|
| E0 | Historical flat RAG baseline | Complete historical artifact | Continuity only |
| E1 | Parent-child corpus + `text-embedding-3-small` | Candidate run complete | Review pending |
| E2 | Replace dense model with `text-embedding-3-large` | Candidate run complete; selected by D014 | Review pending |
| E3 | Add BM25 and equal-weight RRF | Candidate run complete; selected by D015 | Review pending |
| E4 | Rerank fixed hybrid top-20 with local MiniLM | Candidate run complete; selected by D018 | Review pending |
| E5 | Assemble contexts, generate, verify, and calibrate abstention | Two context variants complete; generation not run | Blocked |
| E6 | Optional constrained multi-step retrieval | Not started | Run only for validated residuals |

The supporting BM25 run is complete under `experiments/BM25_local_candidate_v1`. Exact paths, completion timestamps, selected models, seeds, metrics, and blockers are recorded in `configs/experiment_matrix.yaml`.

## Completed and reproducible

- hierarchy-aware corpus with 109 legal parents and 1,535 retrievable children;
- evidence-linked 99-question candidate benchmark with a 42/57 legal-parent grouped split and zero parent leakage;
- BM25, `text-embedding-3-small`, `text-embedding-3-large`, and equal-weight RRF retrieval runs;
- development-only selection of `text-embedding-3-large` and the BM25+dense hybrid;
- local `cross-encoder/ms-marco-MiniLM-L6-v2` reranking over 1,980 query-passage pairs;
- compact top-5 and top-5-with-neighbours context bundles for all 99 candidate questions;
- source-ID-constrained answer schema, evidence prompt, canonical-citation resolution, quote checks, and abstention logging interfaces;
- strict reviewed-benchmark freeze pipeline with alternative evidence-set support and SHA-256 lineage;
- review-watermarked candidate reports and a ten-slide 29 July supervisor narrative;
- multi-reviewer validation protocol D023/D024, bilingual collection form, and aggregation tooling;
- school-compliant LaTeX source with expanded State of the Art and Methodology chapters and 64 bibliography entries;
- 70 automated tests passing as of the last verified run.

## Selected candidate pipeline

1. Retrieve 20 candidates using BM25 plus `text-embedding-3-large`.
2. Fuse rankings with equal-weight reciprocal rank fusion (`k=60`).
3. Rerank the fixed pool locally with the MiniLM cross-encoder.
4. Assemble either compact top-5 or top-5-with-neighbours evidence.
5. After benchmark freeze and authorization, generate a structured evidence-constrained answer.
6. Verify schema, allowed source IDs, verbatim quotes, canonical citations, semantic support, and abstention.
7. Escalate only when an observable failure signal justifies clarification, retrieval expansion, human review, or optional multi-step retrieval.

## Current validity and execution gates

The repository review queue remains **0/33 decided**. D023/D024 replace single-reviewer certification with a bilingual multi-reviewer panel and a pre-registered aggregation rule. Collection tooling and live form links are documented in `review_kit/` and `docs/generated_artifacts_log.md`; external form responses are not counted until exported, aggregated, adjudicated, and written back to the repository queue.

Until the reviewed benchmark is frozen:

- every retrieval percentage remains a candidate result;
- the three top-20 residuals cannot be called a definitive RAG ceiling;
- final test generation remains blocked;
- no candidate watermark may be removed.

Hosted generation has not been authorized, and no generator has been selected. The compact and neighbour-enriched E5 contexts are preparation artifacts, not answer-generation results.

## Immediate milestone

1. Collect at least two independent ratings per reviewed record, aiming for three reviewers.
2. Export and aggregate the form responses with `review_kit/aggregate_reviews.py`.
3. Author-adjudicate contested or correction-flagged records under D024.
4. Write the completed decisions to `data/evaluation/independent_review_v1/review_queue.csv`.
5. Run `scripts/freeze_reviewed_benchmark.py` and inspect the frozen manifest.
6. Recalculate saved retrieval and reranking metrics against the reviewed labels.
7. Update the 29 July presentation and mémoire tables while retaining scope caveats.
8. Select and separately authorize the controlled generator experiment before E5 answer generation.

## Mémoire status

The LaTeX source has advanced beyond the 23 July PDF export: Chapter 2, Chapter 4, and the bibliography were expanded on 25 July. Those additions remain `pending-author-edit`, and the packaged PDF must be rebuilt and visually reviewed before its page count is treated as current. Final Results, Conclusion, abstracts, company context, metadata, and AI-use wording remain provisional.
