"""Validation for evidence-constrained generated answer payloads."""

from __future__ import annotations

ABSTENTION_REASONS = {
    "ambiguous_question",
    "conflicting_sources",
    "insufficient_evidence",
    "outside_corpus",
    "verification_failed",
}


def validate_answer_payload(
    payload: object,
    allowed_source_ids: set[str] | list[str],
) -> list[str]:
    errors: list[str] = []
    allowed = set(allowed_source_ids)
    if not isinstance(payload, dict):
        return ["payload must be an object"]

    answer_text = payload.get("answer_text")
    if not isinstance(answer_text, str):
        errors.append("answer_text must be a string")

    abstain = payload.get("abstain")
    if not isinstance(abstain, bool):
        errors.append("abstain must be a boolean")
        abstain = False

    reason = payload.get("abstention_reason")
    if abstain:
        if reason not in ABSTENTION_REASONS:
            errors.append("abstention_reason is required and must be allowed")
    elif reason not in (None, ""):
        errors.append("abstention_reason must be empty when abstain is false")

    clarification = payload.get("clarification_question")
    if clarification is not None and not isinstance(clarification, str):
        errors.append("clarification_question must be a string or null")

    claims = payload.get("claims")
    if not isinstance(claims, list):
        errors.append("claims must be a list")
        return errors
    if not abstain and not claims:
        errors.append("non-abstaining answers require at least one claim")

    seen_claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be an object")
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            errors.append(f"{prefix}.claim_id must be a non-empty string")
        elif claim_id in seen_claim_ids:
            errors.append(f"{prefix}.claim_id must be unique")
        else:
            seen_claim_ids.add(claim_id)
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            errors.append(f"{prefix}.text must be a non-empty string")
        supports = claim.get("supports")
        if not isinstance(supports, list) or not supports:
            errors.append(f"{prefix}.supports must be a non-empty list")
            continue
        for support_index, support in enumerate(supports):
            support_prefix = f"{prefix}.supports[{support_index}]"
            if not isinstance(support, dict):
                errors.append(f"{support_prefix} must be an object")
                continue
            source_id = support.get("source_id")
            if source_id not in allowed:
                errors.append(f"{support_prefix}.source_id is not allowed")
            quote = support.get("quote")
            if not isinstance(quote, str) or not quote.strip():
                errors.append(f"{support_prefix}.quote must be a non-empty string")
    return errors


def resolve_citations(payload: dict, evidence_by_id: dict[str, dict]) -> list[dict]:
    """Resolve model-selected source IDs to application-controlled citations."""
    resolved: list[dict] = []
    seen: set[str] = set()
    for claim in payload.get("claims", []):
        for support in claim.get("supports", []):
            source_id = support.get("source_id")
            if source_id in seen or source_id not in evidence_by_id:
                continue
            seen.add(source_id)
            evidence = evidence_by_id[source_id]
            resolved.append(
                {
                    "source_id": source_id,
                    "canonical_citation": evidence["canonical_citation"],
                    "document_id": evidence["document_id"],
                    "parent_id": evidence["parent_id"],
                }
            )
    return resolved
