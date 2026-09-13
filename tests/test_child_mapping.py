from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.evaluation import rank_child_candidates, review_priority  # noqa: E402


def child(
    child_id: str,
    sequence: int,
    citation: str,
    text: str,
    parent_id: str = "P1",
) -> dict:
    return {
        "child_id": child_id,
        "parent_id": parent_id,
        "sequence": sequence,
        "canonical_citation": citation,
        "unit_type": "paragraph",
        "text": text,
    }


def test_matching_citation_and_answer_evidence_rank_first():
    qa = {
        "question": "When must the report be submitted?",
        "answer": "The report must be submitted within 72 hours.",
        "citation": "Article 4(7)",
    }
    candidates = rank_child_candidates(
        qa,
        "P1",
        [
            child("C1", 1, "Article 4(6)", "The reporter categories are listed."),
            child(
                "C2",
                2,
                "Article 4(7)",
                "The report shall be made within 72 hours of becoming aware.",
            ),
        ],
    )
    assert candidates[0]["child_id"] == "C2"
    assert candidates[0]["citation_score"] == 1.0


def test_children_from_other_parents_are_not_candidates():
    qa = {"question": "What is required?", "answer": "A report is required.", "citation": ""}
    candidates = rank_child_candidates(
        qa,
        "P1",
        [
            child("C1", 1, "Article 1", "A report is required."),
            child("C2", 1, "Article 2", "A report is required.", parent_id="P2"),
        ],
    )
    assert [candidate["child_id"] for candidate in candidates] == ["C1"]


def test_weak_candidate_remains_high_priority_for_human_review():
    qa = {
        "question": "What happens next?",
        "answer": "A completely paraphrased outcome.",
        "citation": "Article 7",
    }
    candidates = rank_child_candidates(
        qa,
        "P1",
        [child("C1", 1, "Article 4", "Unrelated reporting details.")],
    )
    assert review_priority(candidates) == "high"


def test_empty_candidate_set_is_blocking():
    assert review_priority([]) == "blocking"
