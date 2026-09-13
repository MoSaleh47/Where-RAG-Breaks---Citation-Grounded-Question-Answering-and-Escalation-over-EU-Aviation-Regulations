# Escalation calibration on development data

Status: complete, and the result is negative. Development split, n=42, prompt v2,
`gpt-4o-mini-2024-07-18`. No held-out data was touched.

The question: **which runtime-observable signal justifies escalating instead of
answering?** A signal qualifies only if it can be computed without gold labels at
the moment a user asks the question.

---

## 1. The headline: the sample cannot support a calibrated threshold

The base rate of a wrong answer on development is **9 of 42 (21%)**. Nine error
events is not enough to fit a threshold that anyone should trust, and pretending
otherwise would be the single easiest way to make this thesis indefensible.

Every candidate rule, with Wilson 95% intervals on precision:

| Rule (escalate when true) | Escalated | Precision | Recall |
|---|---|---|---|
| Reranker moved top-1 by ≥2 ranks | 19/42 | 0.42 [0.23, 0.64] | **0.89** |
| Only one claim made | 5/42 | 0.60 [0.23, 0.88] | 0.33 |
| Reranker moved top-1 by ≥5 ranks | 7/42 | 0.43 [0.16, 0.75] | 0.33 |
| Rerank margin ≤ 0.5 | 14/42 | 0.36 [0.16, 0.61] | 0.56 |
| Rerank margin ≤ 1.0 | 18/42 | 0.33 [0.16, 0.56] | 0.67 |
| Model cited ≤ 2 distinct sources | 21/42 | 0.29 [0.14, 0.50] | 0.67 |
| Quote verification failed | 2/42 | **0.00** [0.00, 0.66] | **0.00** |
| Model abstained | 0/42 | — | 0.00 |

Two rules have a lower confidence bound **fractionally** above the 0.21 base rate
— both at 0.23. That is a margin of two percentage points on a bound estimated
from nine error events, and one of the two ("only one claim made") rests on five
escalations in total. Neither is a basis for a threshold; the honest reading is
that the data cannot separate these rules from the base rate, not that two of them
have been shown to beat it.

Every other interval straddles the base rate outright.

The correct conclusion is not "escalate when the reranker moves the top-1 result".
It is: *this benchmark is too small to calibrate an escalation policy, and here is
how much larger it would need to be.*

---

## 2. How much data would be needed

Two-proportion power calculation, α = 0.05, power = 0.80, against the observed
21% base rate:

| To demonstrate precision of | Escalated decisions needed | Questions needed (at the observed 45% escalation rate) |
|---|---|---|
| 0.35 | 172 | ~383 |
| **0.42** (the best observed) | **80** | **~178** |
| 0.50 | 43 | ~96 |
| 0.60 | 25 | ~56 |

The frozen benchmark is 98 records, 42 of them development. To calibrate the most
promising rule at the effect size actually observed, the development split would
need to be roughly **four times larger**, or the benchmark roughly **1.8 times
larger** if calibration used all of it.

This is a concrete, quantified limitation with a stated remedy, which is worth
considerably more in a mémoire than a threshold fitted to nine events.

---

## 3. The finding that does hold: the two checks are orthogonal

| | count |
|---|---|
| Answers that selected the wrong evidence | 9 |
| Answers whose quotes were not grounded | 2 |
| Answers with **both** defects | **0** |
| Answers with either defect | 11 |

Zero overlap. **Quote verification has precision 0.00 and recall 0.00 for
predicting evidence-selection errors**, and the two answers it did reject had
entirely correct evidence.

This is not a disappointment; it is an architectural result. The system has two
independent failure modes:

- **Evidence selection** — the model attaches its claim to the wrong provision.
  Deterministically checkable only against gold, so at runtime it is *not*
  directly observable; it must be predicted from retrieval signals, which is
  exactly what §1 shows cannot yet be done reliably.
- **Quote fidelity** — the model misreports what the provision says.
  Deterministically checkable at runtime with no gold at all.

A verifier that only checks quotes would have passed all nine evidence errors. A
check on evidence selection alone would have passed both quote failures. Both
layers are necessary, and the reason is measured rather than asserted.

---

## 4. What to specify anyway

The escalation policy remains specifiable even though it is uncalibrated. The
defensible position is:

1. **Quote verification failure → do not answer.** This needs no calibration. It
   is deterministic, has no false positives by construction (a quote either
   appears contiguously in the cited source or it does not), and on development it
   fires on 2 of 42 answers. It is cheap and it is correct.
2. **Retrieval-uncertainty escalation → specified, thresholds uncalibrated.**
   Reranker-versus-fusion disagreement is the most promising signal observed and
   should be named as the candidate, with its threshold left explicitly open and
   the power requirement stated.
3. **Model self-abstention → unusable.** Zero abstentions in 84 opportunities
   (D039). It is not a signal.

Report escalation precision *and* recall for every rule, always. A rule that
escalates 45% of questions to catch 89% of errors may be right for aviation
regulation, where a wrong citation is expensive and a referral is cheap — but that
is a domain judgement about the cost ratio, not something the data decides. State
the cost assumption explicitly rather than implying the number chose itself.

---

## 5. Threats to this analysis

1. **Nine events.** Everything in §1 rests on nine errors. Treat every precision
   figure as indicative.
2. **One model, one prompt, one context variant.** The neighbour-enriched context
   set is built and unrun; signal behaviour may differ with broader context.
3. **"Wrong evidence" is defined as the cited source IDs failing to intersect the
   reviewed gold child set.** A record whose gold evidence the review itself found
   contestable inherits that contestability here.
4. **No test-split figure exists and none should**, until a policy is frozen.
   Publishing an escalation number calibrated and evaluated on the same 42 records
   would be circular.
