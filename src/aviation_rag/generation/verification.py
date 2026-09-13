"""Deterministic source, quote, and schema verification.

What "verbatim" means here is a deliberate choice, and it changes the reported
grounding rate by roughly twenty points, so it is stated rather than assumed.

A quote is accepted when its **word sequence appears contiguously** in the source
it points at, after typographic and punctuation normalisation. Two things follow
from that definition:

* Punctuation and typography are ignored. The corpus is a PDF extraction and
  carries its own artefacts -- ``safetyrelated`` appears unhyphenated in the
  source text -- so requiring byte-identical punctuation measures the extractor
  and the model's transcription habits rather than whether the answer is
  grounded. Ending a quote early and closing it with a full stop where the
  source continued with a comma is normal quotation, not a distortion.
* Contiguity is **not** relaxed, and that is the part that does the work. An
  elided quote -- ``"not required... unless the occurrence... resulted in"`` --
  is rejected, because the omitted span can silently delete a condition. On the
  development set every such quote dropped material from a legal test, in one
  case removing an entire limb of an exception while reading perfectly fluently.

``quote_pass_strict`` reports the byte-level result under the original rule so
the stricter claim remains available and the difference between the two can be
reported rather than buried.

None of this establishes that a source *supports* a claim. It establishes only
that the claim points at supplied evidence and reproduces its wording. Semantic
support is a separate question and is flagged as such.
"""

from __future__ import annotations

import re
import unicodedata

from .schema import resolve_citations, validate_answer_payload

WHITESPACE = re.compile(r"\s+")
NON_WORD = re.compile(r"[^\w\s]")

# Typographic variants that carry no legal meaning.
_TYPOGRAPHY = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    " ": " ",
    "‐": "-",
    "‑": "-",
    "‒": "-",
    "–": "-",
    "—": "-",
    "―": "-",
    "−": "-",
}

ELLIPSIS = re.compile(r"\.\.\.|…|\[\s*\.\.\.\s*\]")


def _normalize(value: str) -> str:
    """Whitespace and case only -- the original, strictest rule."""
    return WHITESPACE.sub(" ", value).strip().casefold()


def _normalize_typography(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    for source, target in _TYPOGRAPHY.items():
        value = value.replace(source, target)
    return value


def _normalize_for_matching(value: str) -> str:
    """Typography- and punctuation-insensitive; word order is preserved."""
    value = NON_WORD.sub(" ", _normalize_typography(value))
    return WHITESPACE.sub(" ", value).strip().casefold()


def quote_is_grounded(quote: str, evidence_text: str) -> bool:
    """Does the quote's word sequence appear contiguously in the evidence?"""
    return _normalize_for_matching(quote) in _normalize_for_matching(evidence_text)


def quote_is_verbatim(quote: str, evidence_text: str) -> bool:
    """Byte-level check under the original whitespace-and-case rule."""
    return _normalize(quote) in _normalize(evidence_text)


def contains_elision(quote: str) -> bool:
    """Does the quote mark omitted material with an ellipsis?"""
    return bool(ELLIPSIS.search(quote))


def verify_answer(payload: object, evidence_by_id: dict[str, dict]) -> dict:
    """Verify structural grounding while flagging semantic review as separate."""
    schema_errors = validate_answer_payload(payload, set(evidence_by_id))
    quote_errors: list[str] = []
    strict_errors: list[str] = []
    elided_quotes: list[str] = []
    supported_claim_ids: list[str] = []

    if isinstance(payload, dict):
        for claim in payload.get("claims", []):
            if not isinstance(claim, dict):
                continue
            claim_id = claim.get("claim_id", "?")
            claim_supported = True
            for support in claim.get("supports", []):
                if not isinstance(support, dict):
                    claim_supported = False
                    continue
                source_id = support.get("source_id")
                quote = support.get("quote")
                if (
                    source_id not in evidence_by_id
                    or not isinstance(quote, str)
                    or not quote.strip()
                ):
                    claim_supported = False
                    continue
                evidence_text = evidence_by_id[source_id]["text"]
                if contains_elision(quote):
                    elided_quotes.append(f"{claim_id}: elided quote from {source_id}")
                if not quote_is_grounded(quote, evidence_text):
                    quote_errors.append(
                        f"{claim_id}: quote not found in {source_id}"
                    )
                    claim_supported = False
                if not quote_is_verbatim(quote, evidence_text):
                    strict_errors.append(
                        f"{claim_id}: quote not byte-verbatim in {source_id}"
                    )
            if claim_supported and claim.get("claim_id"):
                supported_claim_ids.append(claim["claim_id"])

    structural_pass = not schema_errors
    quote_pass = not quote_errors
    abstain = isinstance(payload, dict) and payload.get("abstain") is True
    if structural_pass and quote_pass:
        decision = "abstain" if abstain else "accept_structurally"
    else:
        decision = "retry_or_abstain"

    citations = (
        resolve_citations(payload, evidence_by_id)
        if isinstance(payload, dict)
        else []
    )
    return {
        "decision": decision,
        "structural_pass": structural_pass,
        "quote_pass": quote_pass,
        "quote_pass_strict": not strict_errors,
        "schema_errors": schema_errors,
        "quote_errors": quote_errors,
        "strict_quote_errors": strict_errors,
        "elided_quotes": elided_quotes,
        "supported_claim_ids": supported_claim_ids,
        "resolved_citations": citations,
        "semantic_verification_required": not abstain,
    }
