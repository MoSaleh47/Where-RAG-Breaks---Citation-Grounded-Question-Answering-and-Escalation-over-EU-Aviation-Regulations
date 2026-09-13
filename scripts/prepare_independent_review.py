"""Prepare a deterministic independent benchmark-review worksheet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def source_class(parent_id: str) -> str:
    if parent_id.startswith("GM_"):
        return "GM"
    if "_ANNEX" in parent_id:
        return "ANNEX"
    if "_ART_" in parent_id:
        return "ARTICLE"
    return "OTHER"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--children", required=True, type=Path)
    parser.add_argument("--audited-qa", required=True, type=Path)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-per-stratum", type=int, default=2)
    parser.add_argument("--seed", default="aviation-rag-independent-review-v1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    children_path = args.children.resolve()
    audited_path = args.audited_qa.resolve()
    split_path = args.split_manifest.resolve()
    output = args.output.resolve()
    if output.exists() and not args.force:
        raise SystemExit(
            f"Refusing to overwrite existing review worksheet without --force: {output}"
        )

    children = {row["child_id"]: row for row in read_jsonl(children_path)}
    records = read_jsonl(audited_path)
    with split_path.open(encoding="utf-8-sig", newline="") as stream:
        split_by_qa = {row["qa_id"]: row["split"] for row in csv.DictReader(stream)}

    reasons: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if record["audit_decision"] in {
            "ai_rewritten_supported",
            "excluded_invalid",
        }:
            reasons[record["qa_id"]].add("exception_record")
    for qa_id in ("QA_0063", "QA_0080", "QA_0176"):
        reasons[qa_id].add("hybrid_k20_residual")

    strata: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in records:
        if record["audit_decision"] != "ai_provisional_supported":
            continue
        if record["qa_id"] in reasons:
            continue
        split = split_by_qa.get(record["qa_id"], "excluded")
        strata[(source_class(record["parent_id"]), split)].append(record)

    for stratum, candidates in sorted(strata.items()):
        ordered = sorted(
            candidates,
            key=lambda record: hashlib.sha256(
                f"{args.seed}:{record['qa_id']}".encode("utf-8")
            ).hexdigest(),
        )
        for record in ordered[: args.sample_per_stratum]:
            reasons[record["qa_id"]].add(
                f"stratified_unchanged_{stratum[0]}_{stratum[1]}"
            )

    fieldnames = [
        "qa_id",
        "review_reason",
        "split",
        "source_class",
        "audit_decision",
        "question_type",
        "difficulty",
        "question",
        "reference_answer",
        "acceptable_citation",
        "parent_id",
        "gold_child_ids",
        "gold_evidence_text",
        "ai_audit_notes",
        "reviewer_decision",
        "question_clear_and_unambiguous",
        "answer_fully_supported",
        "citation_correct",
        "gold_evidence_complete",
        "alternative_acceptable_child_ids",
        "alternative_evidence_sets_json",
        "corrected_question",
        "corrected_reference_answer",
        "corrected_citation",
        "corrected_parent_id",
        "corrected_gold_child_ids",
        "corrected_evidence_sets_json",
        "review_notes",
        "reviewer_name_or_role",
        "review_date",
    ]
    selected = [
        record for record in records if record["qa_id"] in reasons
    ]
    selected.sort(key=lambda record: record["qa_id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in selected:
            evidence = []
            for child_id in record.get("gold_child_ids", []):
                child = children[child_id]
                evidence.append(
                    f"{child_id} [{child['canonical_citation']}]: {child['text']}"
                )
            writer.writerow(
                {
                    "qa_id": record["qa_id"],
                    "review_reason": ";".join(sorted(reasons[record["qa_id"]])),
                    "split": split_by_qa.get(record["qa_id"], "excluded"),
                    "source_class": source_class(record["parent_id"]),
                    "audit_decision": record["audit_decision"],
                    "question_type": record.get("question_type", ""),
                    "difficulty": record.get("difficulty", ""),
                    "question": record["question"],
                    "reference_answer": record["reference_answer"],
                    "acceptable_citation": record["acceptable_citation"],
                    "parent_id": record["parent_id"],
                    "gold_child_ids": ";".join(record.get("gold_child_ids", [])),
                    "gold_evidence_text": "\n".join(evidence),
                    "ai_audit_notes": record["audit_notes"],
                }
            )

    counts = {
        "total_rows": len(selected),
        "exception_rows": sum(
            "exception_record" in reasons[record["qa_id"]] for record in selected
        ),
        "residual_rows": sum(
            "hybrid_k20_residual" in reasons[record["qa_id"]] for record in selected
        ),
        "stratified_unchanged_rows": sum(
            any(reason.startswith("stratified_unchanged_") for reason in reasons[record["qa_id"]])
            for record in selected
        ),
    }
    requirements = {
        "version": "independent_review_requirements_v1",
        "required_qa_ids": [record["qa_id"] for record in selected],
        "expected_review_row_count": len(selected),
        "selection": {
            "sample_per_stratum": args.sample_per_stratum,
            "seed": args.seed,
        },
        "inputs": {
            "audited_qa_sha256": sha256(audited_path),
            "children_sha256": sha256(children_path),
            "split_manifest_sha256": sha256(split_path),
        },
    }
    output.with_name("review_requirements.json").write_text(
        json.dumps(requirements, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(counts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
