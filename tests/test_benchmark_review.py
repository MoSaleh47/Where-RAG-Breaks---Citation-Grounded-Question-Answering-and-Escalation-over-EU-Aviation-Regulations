from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.evaluation import (  # noqa: E402
    ReviewValidationError,
    apply_review_decisions,
    validate_review_rows,
)


def candidate_records() -> list[dict]:
    return [
        {
            "qa_id": "Q1",
            "question": "Original question?",
            "reference_answer": "Original answer.",
            "acceptable_citation": "Article 1",
            "parent_id": "P1",
            "gold_child_ids": ["C1"],
            "audit_decision": "ai_provisional_supported",
            "independent_human_review": False,
            "source_record_changed": False,
        },
        {
            "qa_id": "Q2",
            "question": "Unselected question?",
            "reference_answer": "Answer.",
            "acceptable_citation": "Article 4",
            "parent_id": "P4",
            "gold_child_ids": ["C4"],
            "audit_decision": "ai_provisional_supported",
            "independent_human_review": False,
            "source_record_changed": False,
        },
    ]


def children() -> dict[str, dict]:
    return {
        "C1": {"child_id": "C1", "parent_id": "P1"},
        "C2": {"child_id": "C2", "parent_id": "P2"},
        "C3": {"child_id": "C3", "parent_id": "P3"},
        "C4": {"child_id": "C4", "parent_id": "P4"},
    }


def valid_row(**overrides: str) -> dict[str, str]:
    row = {
        "qa_id": "Q1",
        "review_reason": "exception_record",
        "reviewer_decision": "accept",
        "question_clear_and_unambiguous": "yes",
        "answer_fully_supported": "yes",
        "citation_correct": "yes",
        "gold_evidence_complete": "yes",
        "alternative_acceptable_child_ids": "",
        "alternative_evidence_sets_json": "",
        "corrected_question": "",
        "corrected_reference_answer": "",
        "corrected_citation": "",
        "corrected_parent_id": "",
        "corrected_gold_child_ids": "",
        "corrected_evidence_sets_json": "",
        "review_notes": "Checked against source.",
        "reviewer_name_or_role": "independent domain reviewer",
        "review_date": "2026-07-24",
    }
    row.update(overrides)
    return row


def test_alternative_evidence_sets_are_preserved_as_or_routes():
    row = valid_row(
        reviewer_decision="accept_with_alternative_evidence",
        gold_evidence_complete="no",
        alternative_acceptable_child_ids="C2",
        alternative_evidence_sets_json='[["C3", "C4"]]',
    )
    retained, summary = apply_review_decisions(
        candidate_records(),
        [row],
        children(),
    )
    reviewed = retained[0]
    assert reviewed["acceptable_evidence_sets"] == [["C1"], ["C2"], ["C3", "C4"]]
    assert reviewed["acceptable_parent_ids"] == ["P1", "P2", "P3", "P4"]
    assert reviewed["independent_human_review"] is True
    assert retained[1]["independent_human_review"] is False
    assert summary["independently_reviewed_retained_count"] == 1
    assert summary["full_benchmark_expert_review_complete"] is False


def test_correction_replaces_primary_evidence_and_tracks_question_change():
    row = valid_row(
        reviewer_decision="correct",
        question_clear_and_unambiguous="no",
        corrected_question="Corrected question?",
        corrected_parent_id="P2",
        corrected_gold_child_ids="C2;C3",
    )
    retained, summary = apply_review_decisions(
        candidate_records(),
        [row],
        children(),
    )
    reviewed = retained[0]
    assert reviewed["question"] == "Corrected question?"
    assert reviewed["parent_id"] == "P2"
    assert reviewed["gold_child_ids"] == ["C2", "C3"]
    assert reviewed["acceptable_evidence_sets"] == [["C2", "C3"]]
    assert summary["changed_question_qa_ids"] == ["Q1"]
    assert summary["changed_parent_qa_ids"] == ["Q1"]


def test_incomplete_review_is_rejected():
    row = valid_row(reviewer_decision="", reviewer_name_or_role="", review_date="")
    with pytest.raises(ReviewValidationError, match="cannot be frozen"):
        validate_review_rows([row], {r["qa_id"]: r for r in candidate_records()}, children())


def test_accept_cannot_hide_supplied_alternatives():
    row = valid_row(alternative_acceptable_child_ids="C2")
    with pytest.raises(ReviewValidationError, match="accept_with_alternative_evidence"):
        validate_review_rows([row], {r["qa_id"]: r for r in candidate_records()}, children())


def test_unknown_evidence_child_is_rejected():
    row = valid_row(
        reviewer_decision="accept_with_alternative_evidence",
        alternative_acceptable_child_ids="MISSING",
    )
    with pytest.raises(ReviewValidationError, match="unknown evidence child"):
        validate_review_rows([row], {r["qa_id"]: r for r in candidate_records()}, children())



def test_requirements_manifest_detects_deleted_review_row():
    row = valid_row()
    with pytest.raises(ReviewValidationError, match="missing required QA IDs"):
        validate_review_rows(
            [row],
            {record["qa_id"]: record for record in candidate_records()},
            children(),
            {"Q1", "Q2"},
        )


def test_freeze_cli_writes_hashed_artifacts(tmp_path: Path):
    audited_path = tmp_path / "audited.jsonl"
    children_path = tmp_path / "children.jsonl"
    review_path = tmp_path / "review.csv"
    requirements_path = tmp_path / "review_requirements.json"
    output = tmp_path / "frozen"

    audited_path.write_text(
        "".join(json.dumps(record) + "\n" for record in candidate_records()),
        encoding="utf-8",
    )
    children_path.write_text(
        "".join(json.dumps(child) + "\n" for child in children().values()),
        encoding="utf-8",
    )
    row = valid_row()
    with review_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)

    requirements = {
        "version": "independent_review_requirements_v1",
        "expected_review_row_count": 1,
        "required_qa_ids": ["Q1"],
        "inputs": {
            "audited_qa_sha256": hashlib.sha256(
                audited_path.read_bytes()
            ).hexdigest().upper(),
            "children_sha256": hashlib.sha256(
                children_path.read_bytes()
            ).hexdigest().upper(),
        },
    }
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "freeze_reviewed_benchmark.py"),
            "--audited-qa",
            str(audited_path),
            "--review-csv",
            str(review_path),
            "--children",
            str(children_path),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "freeze_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert summary["retained_record_count"] == 2
    assert summary["review_queue_count"] == 1
    assert summary["source_group_leakage_count"] == 0
    assert manifest["inputs"]["review_requirements_sha256"]
    assert (output / "reviewed_benchmark.jsonl").is_file()
    assert (output / "split_manifest.csv").is_file()
