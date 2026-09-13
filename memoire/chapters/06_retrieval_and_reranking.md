# Chapter 6 — Retrieval, Fusion, and Reranking

## 6.1 Experimental question

This chapter asks where evidence retrieval fails after repairing corpus hierarchy, and which incremental intervention recovers each failure. The experiment changes one major component at a time:

1. parent-child dense retrieval with text-embedding-3-small;
2. the same corpus and questions with text-embedding-3-large;
3. local BM25 lexical retrieval;
4. equal-weight reciprocal-rank fusion of BM25 and the selected dense model;
5. local cross-encoder reranking of the fused top-20 candidate pool.

Retrieval is evaluated separately from answer generation. A retrieval hit means that at least one selected gold child is present in the top k. This does not imply that a generated answer is legally correct.

## 6.2 Evaluation measures

The reported measures are:

- parent recall: at least one child from the selected legal parent appears;
- any-gold-child recall: at least one selected evidence child appears;
- mean evidence recall: the mean fraction of selected evidence children retrieved;
- reciprocal rank: the inverse rank of the first selected child;
- nDCG: rank-sensitive gain when one or more selected children appear.

The primary operational question is whether exact evidence fits into a small generation context. Recall at k=5 is therefore central. Recall at k=20 measures whether a broader candidate pool contains the evidence needed for reranking.

## 6.3 Dense-model comparison

Both embedding models process the same 1,535 retrieval texts and 99 questions. Input hashes and grouped splits are identical. Each run consumed 172,821 embedding input tokens, and model-specific vectors were cached.

text-embedding-3-large was selected using development data:

| Dense model | Development recall@5 | Development recall@10 |
|---|---:|---:|
| text-embedding-3-small | 66.7% | 76.2% |
| text-embedding-3-large | **69.0%** | **78.6%** |

The larger model also improved development evidence recall and nDCG at these cutoffs. The improvement is modest rather than transformative.

On the held-out candidate test split, large dense retrieval reaches 71.9% at k=5 and 80.7% at k=10. It therefore leaves a substantial retrieval gap after the embedding upgrade.

## 6.4 Lexical retrieval

The BM25 baseline is implemented locally with fixed k1 = 1.5 and b = 0.75. It performs strongly because aviation regulations contain exact terminology, article references, acronyms, deadlines, and repeated formal expressions.

Candidate test exact-child recall is:

| Method | k=5 | k=10 | k=20 |
|---|---:|---:|---:|
| Dense large | 71.9% | 80.7% | 86.0% |
| BM25 | **73.7%** | **84.2%** | 84.2% |

BM25 exceeds the dense baseline at k=5 and k=10 but plateaus at k=20. The channels therefore have complementary strengths.

## 6.5 Reciprocal-rank fusion

Dense and BM25 rankings are combined with equal-weight reciprocal-rank fusion:

$RRF(d) = \sum_i \frac{1}{60 + rank_i(d)}$

The constant is fixed at 60. It was not optimized on test data. Unequal dense-to-BM25 weights were later checked on development; no unequal weight improved the top-20 candidate objective over equal fusion.

Candidate test results are:

| Method | k=5 | k=10 | k=20 |
|---|---:|---:|---:|
| Dense large | 71.9% | 80.7% | 86.0% |
| BM25 | 73.7% | 84.2% | 84.2% |
| Hybrid RRF | **80.7%** | **87.7%** | **94.7%** |

At k=10, hybrid fusion recovers five dense failures while breaking one dense success. Relative to BM25, it recovers five failures and breaks three successes. Fusion improves aggregate recall but is not uniformly superior on every query.

## 6.6 Cross-encoder reranking

The fused top-20 candidates are reranked with cross-encoder/ms-marco-MiniLM-L6-v2. This 22.7M-parameter English passage-ranking model runs locally on an NVIDIA RTX 4070 Laptop GPU. The model scores the question and passage jointly rather than comparing independent embeddings.

No project question or regulatory passage is sent to a hosted inference service. The experiment scores 1,980 query-passage pairs and caches all scores. The exact model commit is recorded in the manifest.

Candidate held-out results are:

| Method | k=1 | k=3 | k=5 | k=10 | k=20 |
|---|---:|---:|---:|---:|---:|
| Hybrid RRF | 50.9% | 75.4% | 80.7% | 87.7% | 94.7% |
| Hybrid + cross-encoder | **66.7%** | **86.0%** | **87.7%** | **93.0%** | 94.7% |

The unchanged k=20 value is expected: reranking can reorder existing candidates but cannot add missing evidence. Its value is moving relevant evidence into a context budget of approximately five children.

At test k=5, reranking recovers five hybrid misses and breaks one hybrid success, for a net gain of four. At k=10, it recovers four and breaks one, for a net gain of three.

## 6.7 Negative reranking ablations

Two simpler score transformations were tested on development before adopting the cross-encoder.

Parent-mass boosting added the accumulated score of every child sharing a parent. It consistently reduced recall because long or repeated guidance sections accumulated score without guaranteeing exact relevance.

Unequal RRF weighting also failed to improve the top-20 objective. A BM25-heavy configuration gained one development question at k=5 but lost recall at deeper cutoffs.

These negative results are methodologically useful. They show that hierarchy awareness is not equivalent to indiscriminately promoting parents and that the observed reranker gain comes from direct query-passage relevance modelling.

## 6.8 Context assembly

Two deterministic generation-context variants are frozen.

| Variant | Mean sources | Mean evidence words | Maximum words |
|---|---:|---:|---:|
| Compact reranked top-5 | 5.0 | 234 | 503 |
| Top-5 plus adjacent children | 11.4 | 473 | 1,090 |

The compact variant tests precise evidence selection. The neighbour variant tests whether local legal continuity improves answer completeness without reintroducing blind parent-level context. Both variants preserve source IDs, hierarchy, canonical citations, document type, and version.

No gold labels are consulted during context assembly.

## 6.9 Residual failure analysis

Three candidate test questions remain outside the top-20 pool.

QA_0063 asks generally what exceptions Regulation 376/2014 notes. Several legitimate exception provisions compete, while the selected answer expects a specific Article 20 interpretation. This is primarily an ambiguity and benchmark-design problem.

QA_0080 asks whether occurrence-category placement limits reporting. Equivalent governing wording appears in another annex child, suggesting incomplete acceptable evidence rather than a simple retrieval failure.

QA_0176 uses broad language about what organisations must do with occurrence information. Many sources share those terms, while the intended GM 3.1 evidence is framed as a safety-benefit discussion. This is a genuine query-to-evidence alignment problem.

The residual therefore combines question ambiguity, incomplete gold labeling, and retrieval failure. It cannot yet be called a single intrinsic RAG ceiling.

## 6.10 Switching-point implication

The experiments support an observable escalation ladder.

If evidence is present in the hybrid top-20 pool but ranked below the generation budget, apply the cross-encoder. If the selected parent appears but the exact child does not, consider neighbouring children or parent-aware expansion. If lexical and dense channels disagree or no credible evidence appears, rewrite or clarify the query. If evidence remains absent, conflicting, or ambiguous, abstain or request human review.

Agentic retrieval is not the default. It is reserved for independently validated residuals that require multi-source decomposition or iterative cross-reference traversal after simpler interventions fail.

## 6.11 Validity statement

All metrics in this chapter are candidate results. The benchmark's 33-row independent review is incomplete. Exact values must be regenerated after corrections, alternative evidence sets, and exclusions are incorporated into a frozen gold version.

Retrieval results do not measure answer correctness. The next controlled phase uses evidence-constrained structured generation, application-resolved citations, verbatim quote checks, semantic claim verification, and selective abstention.
