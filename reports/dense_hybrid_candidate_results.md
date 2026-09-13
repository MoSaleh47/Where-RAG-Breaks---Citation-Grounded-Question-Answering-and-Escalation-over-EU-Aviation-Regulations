# Dense and Hybrid Candidate Retrieval Results

**Run date:** 20 July 2026  
**Corpus:** E1 parent-child v1, 1,535 child units  
**Benchmark:** Legacy-100 AI-assisted candidate, 99 retained questions  
**Split:** Parent-grouped, 42 development and 57 held-out test questions  
**Status:** Candidate evidence. Independent human benchmark review remains pending.

## Executive result

Equal-weight reciprocal rank fusion (RRF) of BM25 and text-embedding-3-large is the strongest tested retriever. On the held-out test split, it retrieves at least one selected gold child for:

- 46/57 questions (80.7%) at k=5;
- 50/57 questions (87.7%) at k=10;
- 54/57 questions (94.7%) at k=20.

This is a retrieval result, not end-to-end answer correctness. It must not be compared directly with the historical 43/100 strict RAG answer score.

The result supports a two-stage design: retrieve a broad hybrid candidate pool of 20, then rerank and pass only a small evidence set to the generator. Feeding all 20 children directly would increase context noise and would not test reranking.

## Controlled model selection

The dense model was selected from development data before interpreting the held-out test result.

### Development exact-child recall

| Retriever | k=1 | k=3 | k=5 | k=10 | k=20 |
|---|---:|---:|---:|---:|---:|
| text-embedding-3-small | 14/42 (33.3%) | 28/42 (66.7%) | 28/42 (66.7%) | 32/42 (76.2%) | 35/42 (83.3%) |
| text-embedding-3-large | 15/42 (35.7%) | 28/42 (66.7%) | 29/42 (69.0%) | 33/42 (78.6%) | 36/42 (85.7%) |
| BM25 | 21/42 (50.0%) | 30/42 (71.4%) | 32/42 (76.2%) | 34/42 (81.0%) | 36/42 (85.7%) |
| BM25 + large RRF | 23/42 (54.8%) | 30/42 (71.4%) | 32/42 (76.2%) | 37/42 (88.1%) | 38/42 (90.5%) |

text-embedding-3-large was selected over text-embedding-3-small because it improves the predeclared exact-child recall measure at k=5 and k=10 on development, and also improves mean evidence recall and nDCG at those cutoffs. The gain is real but modest; the larger embedding model alone does not solve retrieval.

The RRF constant was fixed at 60 with equal weights. It was not tuned on the test set.

## Held-out test results

### Any selected gold child retrieved

| Retriever | k=1 | k=3 | k=5 | k=10 | k=20 |
|---|---:|---:|---:|---:|---:|
| text-embedding-3-small | 27/57 (47.4%) | 32/57 (56.1%) | 35/57 (61.4%) | 43/57 (75.4%) | 50/57 (87.7%) |
| text-embedding-3-large | 25/57 (43.9%) | 34/57 (59.6%) | 41/57 (71.9%) | 46/57 (80.7%) | 49/57 (86.0%) |
| BM25 | 29/57 (50.9%) | 39/57 (68.4%) | 42/57 (73.7%) | 48/57 (84.2%) | 48/57 (84.2%) |
| BM25 + large RRF | 29/57 (50.9%) | 43/57 (75.4%) | 46/57 (80.7%) | 50/57 (87.7%) | 54/57 (94.7%) |

### Complete test metrics for the selected hybrid

| k | Parent recall | Any-gold-child recall | Mean evidence recall | MRR | nDCG |
|---:|---:|---:|---:|---:|---:|
| 1 | 39/57 (68.4%) | 29/57 (50.9%) | 41.4% | 0.509 | 0.509 |
| 3 | 48/57 (84.2%) | 43/57 (75.4%) | 63.2% | 0.626 | 0.590 |
| 5 | 51/57 (89.5%) | 46/57 (80.7%) | 69.2% | 0.638 | 0.608 |
| 10 | 52/57 (91.2%) | 50/57 (87.7%) | 78.7% | 0.646 | 0.644 |
| 20 | 54/57 (94.7%) | 54/57 (94.7%) | 86.0% | 0.651 | 0.664 |

At k=5, RRF improves exact-child recall by 5 questions over the selected dense model and by 4 over BM25. At k=10, it improves by 4 over dense and by 2 over BM25. At k=20, it improves by 5 over dense and by 6 over BM25.

## Recovery and regression analysis

At test k=10:

- relative to text-embedding-3-large, RRF recovers 5 failures and breaks 1 previously successful case, for a net gain of 4;
- relative to BM25, RRF recovers 5 failures and breaks 3 previously successful cases, for a net gain of 2.

Dense failures recovered by RRF are QA_0198, QA_0218, QA_0171, QA_0110, and QA_0240. The dense case lost by fusion is QA_0179.

BM25 failures recovered by RRF are QA_0090, QA_0162, QA_0114, QA_0214, and QA_0118. The BM25 cases lost by fusion are QA_0194, QA_0172, and QA_0071.

This shows why the hybrid result should be reported as a controlled intervention, not as uniformly dominant per query. Fusion raises aggregate recall while still introducing individual ranking regressions.

## Where the hybrid ceiling remains

Seven test questions do not retrieve a selected gold child at k=10:

- QA_0063;
- QA_0071;
- QA_0080;
- QA_0172;
- QA_0176;
- QA_0179;
- QA_0194.

For QA_0071 and QA_0179, the correct parent is present but the selected child is not. This is an observable hierarchy-level signal for reranking or neighbour expansion.

At k=20 only QA_0063, QA_0080, and QA_0176 remain. None has even the selected gold parent in the top 20. Their manual inspection reveals three distinct issues:

1. **QA_0063 ? ambiguous intent.** The question asks generally what exceptions Regulation 376/2014 notes. The selected answer concerns Article 20 access-to-documents exceptions, while the retrievers prioritize other real exception provisions. The question needs narrowing or multiple acceptable evidence sets.
2. **QA_0080 ? incomplete gold evidence.** A highly ranked Annex IV child repeats the same governing wording as the selected Annex I remark and substantively supports the answer. Exact-child scoring currently calls this a miss. The gold set should accept equivalent repeated annex remarks if a domain reviewer confirms them.
3. **QA_0176 ? broad paraphrase and duplicated obligation language.** The question uses generic terms about what organisations must do with occurrence information. Many annex and guidance units use those terms, while the intended GM 3.1 passage is framed as a safety-benefit discussion. This is a genuine query-to-evidence alignment problem and a candidate for query rewriting or reranking.

Therefore, 94.7% must not be described as the intrinsic RAG ceiling. The observed residual combines at least one genuine retrieval problem with ambiguous or incomplete benchmark labels.

## Switching-point interpretation

The experiments support the following evidence-based retrieval policy:

1. Use BM25 plus text-embedding-3-large RRF as the normal retrieval candidate generator.
2. Retrieve 20 candidates because recall rises from 87.7% at k=10 to 94.7% at k=20.
3. Rerank the 20 candidates and select approximately 5 evidence children for generation.
4. Expand neighbours or the legal parent when the correct-looking parent dominates but no decisive child is found.
5. Rewrite or decompose broad questions when dense and lexical results disagree strongly or return many duplicated legal concepts.
6. Abstain or request clarification for ambiguous questions such as QA_0063.
7. Use iterative or agentic retrieval only for a validated residual set after simpler reranking, expansion, and clarification have been measured.

The current evidence does not justify deploying an agent for every question. It justifies a targeted escalation experiment.

## Reproducibility and API accounting

Both embedding runs used the same immutable corpus, audited QA candidate, and grouped split hashes. Each run processed 172,821 API input tokens, for 345,642 total input tokens across the two models.

Cached arrays and metadata are stored under experiments/cache/embeddings/E1_parent_child_v1. Future runs with unchanged input hashes can reuse those vectors without another embedding request.

Saved runs:

- experiments/E1_dense_3small_candidate_v1;
- experiments/E2_dense_3large_candidate_v1;
- experiments/BM25_local_candidate_v1;
- experiments/E3_hybrid_rrf_candidate_v1.

Each experiment stores rankings, split-level metrics, a manifest, input hashes, output hashes, model or fusion parameters, software versions, and candidate-review status.

## Validity limits

- The 99 retained questions are an AI-assisted candidate benchmark, not final expert gold.
- Twenty-one records were rewritten during the evidence audit and one invalid record was excluded.
- Exact-child scoring can undercount substantively equivalent evidence when legal wording repeats.
- Questions and reference answers are synthetic and may reflect generator style.
- Retrieval metrics do not measure answer correctness, citation faithfulness, or legal safety.
- The test set has remained held out for model selection, but reporting it now means future tuning must use development data or create a new untouched confirmation set.

## Required next experiment

Before final claims:

1. independently review the 22 exception records, the three k=20 residuals, and a stratified sample of unchanged records;
2. freeze a human-reviewed gold benchmark version with multiple acceptable evidence sets where justified;
3. rerank the hybrid top 20 to a top-5 context using development data only;
4. run evidence-constrained generation on the frozen test set;
5. measure exact canonical citation, claim support, completeness, abstention, latency, and cost;
6. compare always-simple retrieval with the targeted escalation policy.

This sequence directly answers the research question: where retrieval fails, whether the failure is real or evaluative, and which limited escalation recovers it.

