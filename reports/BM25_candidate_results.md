# Local BM25 Candidate Retrieval Results

**Run date:** 18 July 2026  
**Corpus:** E1 parent-child v1, 1,535 child units  
**Benchmark:** Legacy-100 AI-assisted candidate, 99 retained questions  
**Parameters:** k1 = 1.5, b = 0.75  
**Status:** Candidate result; independent benchmark review is pending.

## Test results

| k | Parent recall | Any-gold-child recall | Mean evidence recall | MRR | nDCG |
|---:|---:|---:|---:|---:|---:|
| 1 | 36/57 (63.2%) | 29/57 (50.9%) | 39.4% | 0.509 | 0.509 |
| 3 | 44/57 (77.2%) | 39/57 (68.4%) | 59.0% | 0.594 | 0.553 |
| 5 | 46/57 (80.7%) | 42/57 (73.7%) | 63.4% | 0.607 | 0.568 |
| 10 | 50/57 (87.7%) | 48/57 (84.2%) | 72.3% | 0.622 | 0.601 |
| 20 | 50/57 (87.7%) | 48/57 (84.2%) | 74.4% | 0.622 | 0.609 |

## All retained questions

At k=5, parent recall is 82/99 (82.8%) and any-gold-child recall is 74/99 (74.7%). At k=10, they rise to 88/99 (88.9%) and 82/99 (82.8%).

## Interpretation

The gap between parent recall and exact-child recall is measurable. At test k=5, four questions retrieve the correct legal parent without retrieving the selected evidence child. This is the hierarchy-aware failure mode that parent-child retrieval is intended to expose.

Increasing k from 10 to 20 does not recover additional test questions, even though mean evidence recall improves slightly. The remaining failures therefore are not simply shallow-ranking misses.

The nine test questions without a gold child at k=10 include:

- vague questions whose key terms occur across many regulations;
- definition questions where guidance material repeats the legal term;
- questions asking about applicability or repeal with highly generic language;
- cross-document timeline questions;
- multi-channel or multi-clause answers where the correct parent appears but the exact evidence child does not.

Representative failure IDs are QA_0063, QA_0080, QA_0090, QA_0114, QA_0118, QA_0162, QA_0176, QA_0179, and QA_0214.

## Research consequence

This local result is already useful for the switching-point research question:

- lexical retrieval succeeds strongly on exact terminology and citation-bearing questions;
- it fails when the query is semantically broad, terminology is duplicated in guidance, or the evidence is structurally distributed;
- parent success without child success is an observable escalation signal;
- deeper retrieval alone has a ceiling on this test view.

The next controlled comparisons are:

1. dense E1 retrieval with text-embedding-3-small;
2. dense E2 retrieval with text-embedding-3-large;
3. BM25 plus dense reciprocal-rank fusion;
4. error recovery versus newly broken correct cases.

## Reproducibility

The experiment directory experiments/BM25_local_candidate_v1 contains rankings.jsonl, retrieval_metrics.json, and manifest.json with input/output hashes. The implementation is dependency-light and fully local.
