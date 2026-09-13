# E5 — evidence-constrained generation, development split

Status: complete on development (n=42). Held-out split not generated; the tooling
refuses it until calibration is frozen (D036).

Model `gpt-4o-mini-2024-07-18`, temperature 0, strict structured output derived
from `schemas/answer_output_v1.schema.json`. Artifacts:
`experiments/E5_generation_top5_dev_v1/` and `.../dev_v2/`, each with
`answers.jsonl`, `generation_summary.json` and a hashed `manifest.json`.

---

## 1. Schema conformance is not a problem, and can be set aside

Across both runs, 84 answers: **0 parse failures, 0 refusals, 0 schema
violations.** Strict structured output at the API level, re-checked locally
against the project's own schema, held in every case.

This matters mainly because it removes a confound. Nothing below is explained by
malformed output; every failure is a failure of *grounding*, not of format.

---

## 2. The prompt fix, measured

v1 asked for a "verbatim supporting quote" and never said what that excluded.
v2 changes exactly one rule: quote one unbroken run of consecutive words, never
use an ellipsis, never join two passages; if the span is long, quote less or give
several separate supports. Nothing else differs.

| | v1 | v2 |
|---|---|---|
| Answers passing quote verification | 32/42 (76.2%) | **40/42 (95.2%)** |
| …under the strict byte-level rule | 23/42 (54.8%) | 31/42 (73.8%) |
| Answers containing an elided quote | 7 | **0** |
| Quote spans | 132 | 133 |
| Claims | 124 | 114 |
| Answer length (words) | 1,714 | 1,535 |

Nine records were repaired. One new failure appeared (§4). The intervention cost
one sentence of prompt and 42 API calls.

Note the claim count fell by 10 while the quote-span count held steady. v2 makes
slightly fewer claims and supports them at the same rate — the constraint appears
to suppress claims the model could not ground, rather than degrading the answers.
That is the desired direction, and it is a development-set observation, not a
proven mechanism.

---

## 3. Two definitions of "verbatim", and why the looser one is primary

Of 132 v1 quote spans: 90 byte-exact, **0** repaired by unicode or curly-quote
normalisation, **31** differing only in punctuation, 11 genuinely wrong.

The zero is the informative number: typography is *not* what breaks these quotes.
The 31 are almost all the model ending a quote early and closing it with a full
stop where the source continued with a comma, or dropping a leading paragraph
marker such as `4.`. Those are ordinary quotation, and the corpus is a PDF
extraction carrying its own artefacts — `safetyrelated` appears unhyphenated in
the source text — so byte-exactness partly measures the extractor.

The verifier therefore matches **contiguous word runs after punctuation and
typography normalisation**, and reports the byte-level result alongside as
`quote_pass_strict`. Word order is never relaxed. Both numbers appear in every
table above; the 21-point gap between them is itself reportable.

---

## 4. The finding worth a section: an unmarked splice

v2 removed every *marked* elision. It introduced one **unmarked** one.

QA_0294, claim_2. The model quoted:

> "who have the role to verify compliance with applicable design data and the
> responsibility to perform investigations with the holder of the type-certificate
> or design approval."

The source reads:

> "…covering persons engaged in manufacturing of an aircraft… **who are directly
> involved in the production of aeronautical items,** have the role to verify
> compliance with applicable design data…"

Told not to write "...", the model did not quote a shorter continuous span. It
spliced two fragments together and left no marker at all — deleting the clause
that limits the provision to persons *directly involved in production*.

**This is why the contiguity check is the load-bearing part of the verifier, and
an ellipsis detector is not.** A regular expression for `...` would have passed
this answer. Only checking that the word sequence actually appears contiguously
in the source catches it. It also shows that a prompt constraint can displace a
failure mode into a less visible form rather than removing it — which is an
argument for verification over instruction, and it is the argument the whole
project makes.

The other remaining failure, QA_0047, is plainer: one claim asserts that "Member
States and EASA are not allowed to record personal details in their databases",
attributed to a source that says only that organisations must keep occurrence
details confidential. That is fabrication, and the same structural check catches
it for the same reason.

---

## 5. The model never abstains

**Abstention count: 0 of 42 in v1. 0 of 42 in v2.**

The schema offers four abstention reasons, the prompt instructs the model to use
them when evidence is insufficient, ambiguous, conflicting or out of scope, and
strict structured output guarantees it *could* return one at no cost. It never
did — not on the record where it fabricated a prohibition, not on the record
where it spliced away a limiting clause.

This is the empirical case for the escalation layer, and it is stronger than the
retrieval numbers. A model given an explicit, free, well-formed channel for
saying "I cannot answer this from the supplied evidence" did not use it once in
84 opportunities, including on answers that were demonstrably ungrounded.
**Abstention cannot be delegated to the generator's own judgement; it has to be
driven by external verification.**

State this plainly in Chapter 5 and again in the conclusion. It converts the
abstention component from a design preference into a measured necessity.

---

## 6. Caveats

1. **Development only, n=42.** No held-out number exists yet and none should
   until thresholds are fixed. `run_generation.py` enforces this rather than
   trusting it.
2. **v2 was selected after seeing v1's failures on development.** That is
   legitimate — it is what development data is for — but it must be described as
   development-set selection, not as an independent result. The held-out run will
   use v2, and that will be its first exposure to unseen data.
3. **Structural verification is not semantic verification.** Everything above
   establishes that a claim points at supplied evidence and reproduces its
   wording contiguously. Whether the evidence *supports* the claim is a separate
   question this run does not answer.
4. **One model, one variant, one temperature.** The neighbour-enriched context
   variant exists and is unrun. Comparing it is cheap and would test whether the
   grounding rate is sensitive to context breadth.
