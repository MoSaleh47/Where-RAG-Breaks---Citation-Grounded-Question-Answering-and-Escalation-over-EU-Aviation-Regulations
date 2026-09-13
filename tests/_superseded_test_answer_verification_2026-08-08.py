from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.generation import (  # noqa: E402
    resolve_citations,
    validate_answer_payload,
    verify_answer,
)


def evidence():
    return {
        "C1": {
            "source_id": "C1",
            "parent_id": "P1",
            "canonical_citation": "Article 1(1)",
            "document_id": "DOC1",
            "text": "Organisations shall report the occurrence within 72 hours.",
        }
    }


def valid_payload():
    return {
        "answer_text": "The occurrence must be reported within 72 hours.",
        "claims": [
            {
                "claim_id": "CL1",
                "text": "Reporting is required within 72 hours.",
                "supports": [
                    {
                        "source_id": "C1",
                        "quote": "shall report the occurrence within 72 hours",
                    }
                ],
            }
        ],
        "abstain": False,
        "abstention_reason": None,
        "clarification_question": None,
    }


def test_valid_payload_and_quotes_pass_structural_verification():
    payload = valid_payload()
    report = verify_answer(payload, evidence())
    assert validate_answer_payload(payload, {"C1"}) == []
    assert report["decision"] == "accept_structurally"
    assert report["quote_pass"] is True
    assert report["semantic_verification_required"] is True


def test_unknown_source_is_rejected():
    payload = valid_payload()
    payload["claims"][0]["supports"][0]["source_id"] = "C9"
    errors = validate_answer_payload(payload, {"C1"})
    assert "claims[0].supports[0].source_id is not allowed" in errors


def test_non_verbatim_quote_triggers_retry_or_abstain():
    payload = valid_payload()
    payload["claims"][0]["supports"][0]["quote"] = "must immediately notify everyone"
    report = verify_answer(payload, evidence())
    assert report["decision"] == "retry_or_abstain"
    assert report["quote_pass"] is False


def test_abstention_requires_an_allowed_reason():
    payload = {
        "answer_text": "",
        "claims": [],
        "abstain": True,
        "abstention_reason": "insufficient_evidence",
        "clarification_question": None,
    }
    assert validate_answer_payload(payload, {"C1"}) == []
    payload["abstention_reason"] = "guess"
    assert validate_answer_payload(payload, {"C1"})


def test_citations_are_resolved_from_sources_not_generated_text():
    citations = resolve_citations(valid_payload(), evidence())
    assert citations == [
        {
            "source_id": "C1",
            "canonical_citation": "Article 1(1)",
            "document_id": "DOC1",
            "parent_id": "P1",
        }
    ]
