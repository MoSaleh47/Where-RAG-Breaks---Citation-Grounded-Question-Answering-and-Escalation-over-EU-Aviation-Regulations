# Multi-reviewer benchmark validation — protocol

**Register this BEFORE sending the form to anyone.** Pre-registration is the whole
difference between a protocol and a post-hoc rationalisation, and it is the first
thing a jury will probe when you say your gold set was validated.

Append to `aviation_rag_research/docs/decision_log.md`:

| Date | ID | Decision | Evidence/rationale | Consequence | Status |
|---|---|---|---|---|---|
| 2026-07-25 | D023 | Replace single-reviewer adjudication with a multi-reviewer panel of practising aviation professionals, collected through a bilingual FR/EN form, with the aggregation rule fixed in advance. | A single author-reviewer cannot answer the objection that the benchmark is AI-generated and AI-audited; multiple independent raters yield a measurable agreement statistic and turn ambiguous records into evidence rather than noise. | Records clear the validity gate only under the pre-registered rule below; contested records are adjudicated by the author and reported separately. | accepted |
| 2026-07-25 | D024 | Treat inter-rater disagreement as a reportable finding, not as noise to be resolved away. | Disagreement on a record is direct empirical evidence that the question is ambiguous — the same argument already made for QA_0063 on internal grounds. | Report agreement statistics and list contested records in the results chapter and in the limitations section. | accepted |

## Pre-registered aggregation rule

Fixed on **25 July 2026**, before any response was collected.

1. **Minimum raters.** A record is auto-decided only with **≥ 2 independent raters**. Fewer → author adjudication.
2. **Rule.** Strict majority on the overall decision *and* on each of the four validity checks. Ties are contested.
3. **Accept.** `accept` requires a majority `accept` **and** all four checks resolving to `yes` — matching the constraint already enforced by `src/aviation_rag/evaluation/review.py`.
4. **Exclude.** A majority `reject` maps to `exclude`.
5. **Correct.** A majority "accept with correction" is **never** auto-applied. The panel identifies the problem; the author writes the corrected fields, because corrections cannot come from a multiple-choice form.
6. **Contested.** Any disagreement → author adjudication, recorded with a written justification, and **reported separately from panel-cleared records**.
7. **Author's own ratings.** If you also fill the form, submit under your own name and report panel results both with and without your ratings. Do not quietly fold yourself into "the panel".

Changing this rule after seeing responses is legitimate only if you say so explicitly and report both versions.

## What to report in the mémoire

- number of reviewers, their experience and familiarity with Reg. (EU) 376/2014;
- records rated per reviewer (partial responses are expected — say so);
- exact agreement percentage, and Cohen's κ (2 raters) or Fleiss' κ (≥3);
- panel-cleared vs author-adjudicated counts;
- the contested records, individually, with what the disagreement was about.

That last item is your strongest material. A record two aviation professionals
disagree about is a *demonstrated* ambiguous question — which is precisely the
claim you make about QA_0063 from internal evidence only. External disagreement
turns an assertion into a measurement.

## Honest limitations to state up front

- The panel is a convenience sample of colleagues, not a randomised expert panel.
- Raters see the AI-proposed answer and evidence, so anchoring toward acceptance is possible. An unanchored design would show only the question and the full regulation — rejected here as too costly for the available reviewer time. **State this trade-off; do not hide it.**
- 33 records is a stratified sample of 99, not a full re-validation.
- Partial completion means per-record rater counts vary; report the distribution.

## Interpreting κ

Landis & Koch: ≤0.20 slight · 0.21–0.40 fair · 0.41–0.60 moderate · 0.61–0.80 substantial · >0.80 almost perfect.

A **low κ is not a failed review**. On a benchmark where you argue ambiguity is
real and consequential, moderate agreement is the expected and interesting
result. Report it as a finding; do not chase a high number by coaching raters.
