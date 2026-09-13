"""Validation and application of independent benchmark-review decisions."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date

ALLOWED_DECISIONS = {
    "accept",
    "accept_with_alternative_evidence",
    "correct",
    "exclude",
}
CHECK_FIELDS = (
    "question_clear_and_unambiguous",
    "answer_fully_supported",
    "citation_correct",
    "gold_evidence_complete",
)
ALLOWED_CHECK_VALUES = {"yes", "no", "uncertain"}


class ReviewValidationError(ValueError):
    """Raised when a review queue is incomplete or internally inconsistent."""


def _split_ids(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(";") if value.strip()]


def _json_evidence_sets(raw: str, field_name: str) -> list[list[str]]:
    if not raw.strip():
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ReviewValidationError(f"{field_name} is not valid JSON: {error}") from error
    if not isinstance(value, list) or any(
        not isinstance(item, list)
        or not item
        or any(not isinstance(child_id, str) or not child_id.strip() for child_id in item)
        for item in value
    ):
        raise ReviewValidationError(
            f"{field_name} must be a JSON list of non-empty child-ID lists"
        )
    return [[child_id.strip() for child_id in item] for item in value]


def _deduplicate_sets(evidence_sets: list[list[str]]) -> list[list[str]]:
    result: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for evidence_set in evidence_sets:
        normalized = tuple(dict.fromkeys(evidence_set))
        if normalized not in seen:
            seen.add(normalized)
            result.append(list(normalized))
    return result


def evidence_sets_from_review(row: dict[str, str], corrected: bool = False) -> list[list[str]]:
    """Parse alternative or corrected evidence-set fields from one CSV row."""
    prefix = "corrected_" if corrected else "alternative_"
    sets: list[list[str]] = []
    ids_field = f"{prefix}gold_child_ids" if corrected else "alternative_acceptable_child_ids"
    raw_ids = _split_ids(row.get(ids_field, ""))
    if raw_ids:
        if corrected:
            sets.append(raw_ids)
        else:
            sets.extend([[child_id] for child_id in raw_ids])
    json_field = f"{prefix}evidence_sets_json"
    sets.extend(_json_evidence_sets(row.get(json_field, ""), json_field))
    return _deduplicate_sets(sets)


def validate_review_rows(
    review_rows: list[dict[str, str]],
    candidate_by_id: dict[str, dict],
    child_by_id: dict[str, dict],
    expected_qa_ids: set[str] | None = None,
) -> None:
    """Reject incomplete, invalid, duplicated, or unsupported review decisions."""
    errors: list[str] = []
    seen: set[str] = set()
    known_parents = {child["parent_id"] for child in child_by_id.values()}

    for line_number, row in enumerate(review_rows, start=2):
        qa_id = row.get("qa_id", "").strip()
        label = qa_id or f"CSV line {line_number}"
        if not qa_id or qa_id not in candidate_by_id:
            errors.append(f"{label}: unknown or missing qa_id")
            continue
        if qa_id in seen:
            errors.append(f"{label}: duplicate review row")
            continue
        seen.add(qa_id)

        decision = row.get("reviewer_decision", "").strip()
        if decision not in ALLOWED_DECISIONS:
            errors.append(
                f"{label}: reviewer_decision must be one of {sorted(ALLOWED_DECISIONS)}"
            )
        for field in CHECK_FIELDS:
            value = row.get(field, "").strip()
            if value not in ALLOWED_CHECK_VALUES:
                errors.append(f"{label}: {field} must be yes, no, or uncertain")
        if not row.get("reviewer_name_or_role", "").strip():
            errors.append(f"{label}: reviewer_name_or_role is required")
        raw_date = row.get("review_date", "").strip()
        try:
            date.fromisoformat(raw_date)
        except ValueError:
            errors.append(f"{label}: review_date must use YYYY-MM-DD")

        try:
            alternatives = evidence_sets_from_review(row)
            corrections = evidence_sets_from_review(row, corrected=True)
        except ReviewValidationError as error:
            errors.append(f"{label}: {error}")
            alternatives, corrections = [], []

        if decision == "accept" and any(
            row.get(field, "").strip() != "yes" for field in CHECK_FIELDS
        ):
            errors.append(f"{label}: accept requires all four validity checks to be yes")
        if decision == "accept" and alternatives:
            errors.append(
                f"{label}: use accept_with_alternative_evidence when alternatives are supplied"
            )
        if decision == "accept_with_alternative_evidence":
            if not alternatives:
                errors.append(f"{label}: at least one alternative evidence set is required")
            for field in CHECK_FIELDS[:3]:
                if row.get(field, "").strip() != "yes":
                    errors.append(f"{label}: {field} must be yes for this decision")
        corrected_fields = (
            "corrected_question",
            "corrected_reference_answer",
            "corrected_citation",
            "corrected_parent_id",
            "corrected_gold_child_ids",
            "corrected_evidence_sets_json",
        )
        if decision == "correct" and not any(
            row.get(field, "").strip() for field in corrected_fields
        ):
            errors.append(f"{label}: correct requires at least one corrected field")

        all_sets = alternatives + corrections
        unknown_children = sorted(
            {
                child_id
                for evidence_set in all_sets
                for child_id in evidence_set
                if child_id not in child_by_id
            }
        )
        if unknown_children:
            errors.append(f"{label}: unknown evidence child IDs {unknown_children}")
        corrected_parent = row.get("corrected_parent_id", "").strip()
        if corrected_parent and corrected_parent not in known_parents:
            errors.append(f"{label}: unknown corrected_parent_id {corrected_parent}")

    if expected_qa_ids is not None:
        missing = sorted(expected_qa_ids - seen)
        unexpected = sorted(seen - expected_qa_ids)
        if missing:
            errors.append(f"review queue is missing required QA IDs {missing}")
        if unexpected:
            errors.append(f"review queue contains unexpected QA IDs {unexpected}")

    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:30])
        remaining = len(errors) - 30
        suffix = f"\n- ... and {remaining} more errors" if remaining > 0 else ""
        raise ReviewValidationError(
            f"Independent review cannot be frozen ({len(errors)} errors):\n{preview}{suffix}"
        )


def apply_review_decisions(
    candidate_records: list[dict],
    review_rows: list[dict[str, str]],
    child_by_id: dict[str, dict],
    expected_qa_ids: set[str] | None = None,
) -> tuple[list[dict], dict]:
    """Apply validated decisions and return retained benchmark records plus a summary."""
    candidate_by_id = {record["qa_id"]: record for record in candidate_records}
    validate_review_rows(review_rows, candidate_by_id, child_by_id, expected_qa_ids)
    review_by_id = {row["qa_id"].strip(): row for row in review_rows}

    retained: list[dict] = []
    excluded_ids: list[str] = []
    changed_question_ids: list[str] = []
    changed_parent_ids: list[str] = []
    decision_counts = {decision: 0 for decision in sorted(ALLOWED_DECISIONS)}

    for original in candidate_records:
        qa_id = original["qa_id"]
        row = review_by_id.get(qa_id)
        if row is None:
            if original["audit_decision"] == "excluded_invalid":
                continue
            record = deepcopy(original)
            decision = None
        else:
            decision = row["reviewer_decision"].strip()
            decision_counts[decision] += 1
            if decision == "exclude":
                excluded_ids.append(qa_id)
                continue
            record = deepcopy(original)
            if decision == "correct":
                replacements = {
                    "question": row.get("corrected_question", "").strip(),
                    "reference_answer": row.get("corrected_reference_answer", "").strip(),
                    "acceptable_citation": row.get("corrected_citation", "").strip(),
                    "parent_id": row.get("corrected_parent_id", "").strip(),
                }
                for field, value in replacements.items():
                    if value:
                        if field == "question" and value != record[field]:
                            changed_question_ids.append(qa_id)
                        if field == "parent_id" and value != record[field]:
                            changed_parent_ids.append(qa_id)
                        record[field] = value
                record["source_record_changed"] = True

        primary = list(record.get("gold_child_ids", []))
        evidence_sets: list[list[str]] = [primary] if primary else []
        if row is not None:
            corrected_sets = evidence_sets_from_review(row, corrected=True)
            alternatives = evidence_sets_from_review(row)
            if decision == "correct" and corrected_sets:
                primary = corrected_sets[0]
                evidence_sets = corrected_sets
                record["gold_child_ids"] = primary
            evidence_sets.extend(alternatives)
        evidence_sets = _deduplicate_sets(evidence_sets)
        if not evidence_sets:
            raise ReviewValidationError(f"{qa_id}: retained record has no acceptable evidence")

        unknown = sorted(
            {
                child_id
                for evidence_set in evidence_sets
                for child_id in evidence_set
                if child_id not in child_by_id
            }
        )
        if unknown:
            raise ReviewValidationError(f"{qa_id}: unknown evidence child IDs {unknown}")

        evidence_parents = [
            child_by_id[child_id]["parent_id"]
            for evidence_set in evidence_sets
            for child_id in evidence_set
        ]
        parent_ids = list(dict.fromkeys([record["parent_id"], *evidence_parents]))
        record["acceptable_evidence_sets"] = evidence_sets
        record["acceptable_parent_ids"] = parent_ids

        if row is None:
            record["independent_human_review"] = False
            record["review_status"] = "not_selected_for_independent_review"
        else:
            record["independent_human_review"] = True
            record["review_status"] = "independently_reviewed"
            record["audit_decision"] = {
                "accept": "human_review_accepted",
                "accept_with_alternative_evidence": (
                    "human_review_accepted_with_alternative_evidence"
                ),
                "correct": "human_review_corrected",
            }[decision]
            record["review_provenance"] = {
                "decision": decision,
                "review_reason": row.get("review_reason", ""),
                "reviewer_name_or_role": row["reviewer_name_or_role"].strip(),
                "review_date": row["review_date"].strip(),
                "review_notes": row.get("review_notes", "").strip(),
            }
        retained.append(record)

    summary = {
        "status": "reviewed_exceptions_and_stratified_sample",
        "input_record_count": len(candidate_records),
        "retained_record_count": len(retained),
        "review_queue_count": len(review_rows),
        "independently_reviewed_retained_count": sum(
            record["independent_human_review"] for record in retained
        ),
        "unreviewed_retained_count": sum(
            not record["independent_human_review"] for record in retained
        ),
        "decision_counts": decision_counts,
        "excluded_qa_ids": sorted(excluded_ids),
        "changed_question_qa_ids": sorted(changed_question_ids),
        "changed_parent_qa_ids": sorted(changed_parent_ids),
        "full_benchmark_expert_review_complete": all(
            record["independent_human_review"] for record in retained
        ),
    }
    return retained, summary

