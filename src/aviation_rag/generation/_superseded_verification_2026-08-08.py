"""Deterministic source, quote, and schema verification."""

from __future__ import annotations

import re

from .schema import resolve_citations, validate_answer_payload

WHITESPACE = re.compile(r"\s+")


def _normalize(value: str) -> str:
    return WHITESPACE.sub(" ", value).strip().casefold()


def verify_answer(payload: object, evidence_by_id: dict[str, dict]) -> dict:
    """Verify structural grounding while flagging semantic review as separate."""
    schema_errors = validate_answer_payload(payload, set(evidence_by_id))
    quote_errors: list[str] = []
    supported_claim_ids: list[str] = []

    if isinstance(payload, dict):
        for claim in payload.get("claims", []):
            if not isinstance(claim, dict):
                continue
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
                evidence_text = _normalize(evidence_by_id[source_id]["text"])
                normalized_quote = _normalize(quote)
                if normalized_quote not in evidence_text:
                    quote_errors.append(
                        f"{claim.get('claim_id', '?')}: quote not found in {source_id}"
                    )
                    claim_supported = False
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
        "schema_errors": schema_errors,
        "quote_errors": quote_errors,
        "supported_claim_ids": supported_claim_ids,
        "resolved_citations": citations,
        "semantic_verification_required": not abstain,
    }
