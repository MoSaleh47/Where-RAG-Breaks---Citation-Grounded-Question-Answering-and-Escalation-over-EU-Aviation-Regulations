# Cross-Encoder Reranking Candidate Results

**Run date:** 22 July 2026  
**Candidate generator:** Equal-weight BM25 + text-embedding-3-large RRF  
**Reranker:** cross-encoder/ms-marco-MiniLM-L6-v2  
**Candidate pool:** Top 20 hybrid children per question  
**Benchmark:** Legacy-100 AI-assisted candidate, 99 retained questions  
**Status:** Candidate evidence; independent human benchmark review remains pending.

## Executive result

The local cross-encoder materially improves ranking quality without changing candidate generation.

On the held-out 57-question test split:

| Method | k=1 | k=3 | k=5 | k=10 | k=20 |
|---|---:|---:|---:|---:|---:|
| Hybrid RRF | 29/57 (50.9%) | 43/57 (75.4%) | 46/57 (80.7%) | 50/57 (87.7%) | 54/57 (94.7%) |
| Hybrid + cross-encoder | **38/57 (66.7%)** | **49/57 (86.0%)** | **50/57 (87.7%)** | **53/57 (93.0%)** | 54/57 (94.7%) |

The main gain is not deeper retrieval. It is moving relevant evidence toward the top of an already strong candidate pool. Recall@20 remains unchanged because reranking cannot introduce evidence that the hybrid retriever did not retrieve.

## Why this reranker

The selected model is a 22.7M-parameter English cross-encoder trained for MS MARCO passage ranking. It is small enough for fast local evaluation and matches the current English-question, English-corpus scope.

Official model card: https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2

The larger multilingual BGE reranker was not selected because multilingual scope is still pending supervisor confirmation and its model repository is approximately 2.29 GB. Adding that cost before defining the multilingual experiment would not be controlled.

The model was chosen before examining its test result. There are no learned project-specific weights and no test-tuned thresholds.

## Development result

| Method | k=1 | k=3 | k=5 | k=10 | k=20 |
|---|---:|---:|---:|---:|---:|
| Hybrid RRF | 23/42 (54.8%) | 30/42 (71.4%) | 32/42 (76.2%) | 37/42 (88.1%) | 38/42 (90.5%) |
| Hybrid + cross-encoder | **28/42 (66.7%)** | **35/42 (83.3%)** | **36/42 (85.7%)** | **38/42 (90.5%)** | 38/42 (90.5%) |

The improvement appears on development as well as test, reducing concern that the test gain is an isolated fluctuation.

## Complete selected test metrics

| k | Parent recall | Any-gold-child recall | Mean evidence recall | MRR | nDCG |
|---:|---:|---:|---:|---:|---:|
| 1 | 46/57 (80.7%) | 38/57 (66.7%) | 53.7% | 0.667 | 0.667 |
| 3 | 51/57 (89.5%) | 49/57 (86.0%) | 74.4% | 0.751 | 0.709 |
| 5 | 52/57 (91.2%) | 50/57 (87.7%) | 78.2% | 0.755 | 0.720 |
| 10 | 54/57 (94.7%) | 53/57 (93.0%) | 84.2% | 0.761 | 0.740 |
| 20 | 54/57 (94.7%) | 54/57 (94.7%) | 86.0% | 0.762 | 0.745 |

For generation, top-5 is the practical context budget candidate. The cross-encoder raises exact-child recall there by four net questions while also improving mean evidence recall and ranking quality.

## Recovery and regression analysis

At test k=5, reranking recovers five hybrid misses:

- QA_0198;
- QA_0171;
- QA_0172;
- QA_0179;
- QA_0214.

It breaks one hybrid success, QA_0287, for a net gain of four questions.

At test k=10, reranking recovers:

- QA_0194;
- QA_0172;
- QA_0179;
- QA_0071.

It breaks QA_0162, for a net gain of three questions.

The regressions matter. A general-domain passage reranker is not uniformly reliable for legal evidence, so the project should preserve the original hybrid rank and expose reranker disagreement as a verification signal.

## Residual ceiling

At k=10 the remaining failures are QA_0063, QA_0080, QA_0162, and QA_0176.

At k=20 the same three candidate-generation residuals remain as before:

- QA_0063: under-specified exception question;
- QA_0080: likely incomplete gold evidence because equivalent annex wording exists;
- QA_0176: broad query-to-evidence alignment failure.

The cross-encoder can recover ranking failures but cannot repair an absent candidate, ambiguous question, or incomplete benchmark label.

This cleanly separates two escalation points:

1. **Candidate is present but ranked too low:** use the cross-encoder.
2. **Candidate is absent from the top 20:** use query clarification, query rewriting, cross-reference or neighbour expansion, or abstention.

## Negative development-only ablations

Two simpler alternatives were tested before downloading a reranker:

- adding parent-level candidate mass to each child score;
- changing the dense-to-BM25 weight in reciprocal-rank fusion.

Parent-mass boosting consistently reduced development recall because long or repetitive legal parents accumulated score regardless of exact relevance.

Unequal RRF weights did not improve the top-20 development objective. Equal weighting remained strongest at k=10 and k=20. A BM25-heavy setting gained one question at k=5 but lost recall at deeper candidate cutoffs.

These negative results justify using an actual query-passage cross-encoder rather than presenting score reshuffling as reranking.

## Runtime and data handling

- 1,980 query-passage pairs were scored.
- Inference ran locally on an NVIDIA GeForce RTX 4070 Laptop GPU.
- No project question or regulation passage was sent to a hosted inference API.
- Only the public model weights were downloaded.
- Scores are cached under experiments/cache/rerankers/ms-marco-MiniLM-L6-v2.
- The exact model commit is c5ee24cb16019beea0893ab7796b1df96625c6b8.

## Reproducibility

The experiment directory experiments/E4_cross_encoder_rerank_candidate_v1 contains:

- rankings.jsonl with original hybrid rank and cross-encoder score;
- retrieval_metrics.json with development, test, and combined metrics;
- manifest.json with input/output hashes, model revision, hardware, parameters, and cache hash.

The reranking implementation is in scripts/run_cross_encoder_reranking.py. Deterministic score ordering is unit-tested.

## Research consequence

The evidence now supports a concrete, economical escalation ladder:

1. generate candidates with BM25 + text-embedding-3-large RRF;
2. retrieve 20 candidates;
3. rerank them locally with the MiniLM cross-encoder;
4. pass approximately five children to evidence-constrained generation;
5. verify claims and canonical source IDs;
6. clarify, expand, or abstain when evidence is absent or ambiguous;
7. reserve agentic retrieval for validated multi-step residuals.

This is stronger than simply comparing systems. It identifies a measurable switching point: reranking is valuable when evidence exists in the top-20 pool but is outside the context budget.

## Remaining validity gate

These metrics remain candidate results until the 33-row independent-review worksheet is completed and incorporated. That review includes every prior exception, every k=20 residual, and deterministic unchanged controls.

Do not quote the percentages as final m?moire accuracy until the reviewed gold benchmark is frozen.
