# Research Protocol

## Primary question

Where and why does retrieval-augmented generation fail in citation-bearing aviation-regulation QA, and which observable conditions justify escalating from standard RAG to advanced retrieval, verification, constrained multi-step reasoning, or human review?

## Unit of analysis

The primary unit is one question/system prediction. Retrieval analysis additionally operates on ranked child and parent source IDs. Parallel French/English questions are paired observations.

## Comparison policy

- E0 remains the frozen historical baseline.
- E1–E6 follow the committed ablation order.
- Only one major component changes between adjacent experiments.
- Retrieval configurations are selected using retrieval metrics, not end-to-end answer scores.
- End-to-end generation is run only for shortlisted retrieval configurations.
- Hyperparameters are selected on development data, never on the final gold test set.

## Data-split policy

- Split by source parent/article, not only by QA ID.
- Fine-tuning, few-shot demonstrations, and development examples must not share a source parent with final test questions.
- The legacy sample is never represented as leakage-free.

## Evaluation policy

Report these dimensions independently:

1. gold evidence retrieved;
2. exact and partial citation correctness;
3. factual answer correctness;
4. claim-level groundedness;
5. completeness;
6. unsupported claims;
7. abstention correctness;
8. latency, tokens, and cost.

ROUGE-L and the legacy threshold are continuity metrics only. They are not substitutes for legal correctness.

## Statistical policy

- Report the denominator and evaluation view beside every percentage.
- Add Wilson or bootstrap confidence intervals as appropriate.
- Use paired comparisons because systems answer the same questions.
- Treat small subgroups as exploratory and always report N.
- Do not make causal claims without an intervention that isolates the factor.

## Switching-policy evaluation

Runtime triggers may use retrieval confidence, dense/BM25 disagreement, query structure, cross-reference detection, evidence conflicts, verifier failure, and ambiguity. They may not use the hidden gold source.

Evaluate:

- baseline failures recovered;
- correct baseline answers broken;
- escalation precision and recall;
- accuracy/risk versus coverage;
- incremental latency and cost by escalation level.

## Human review

D023/D024 define the current validity gate. The 33-record queue is reviewed through a bilingual panel of practising aviation professionals under a rule fixed before collection. A record requires at least two independent raters for an automatic panel decision; three reviewers are targeted so Fleiss' kappa can be reported. Strict majority is required for the overall decision and each validity check. Correction-flagged, tied, or otherwise contested records are author-adjudicated with a written justification and reported separately from panel-cleared records.

Report reviewer roles, coverage per record, exact agreement, Cohen's or Fleiss' kappa as applicable, panel-cleared versus adjudicated counts, and every contested record. The repository queue is currently 0/33 decided; external form responses are not evidence until aggregated and written back. No final benchmark claim is permitted before the freeze command succeeds.

## Stop conditions

- Freeze major experiments by 9 August 2026.
- Do not add agentic RAG without enough validated multi-source questions and evidence that simpler interventions leave a residual failure.
- Abstain rather than produce unsupported legal/compliance guidance.

