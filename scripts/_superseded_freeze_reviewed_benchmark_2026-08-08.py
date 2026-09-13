"""Freeze a validated benchmark after the bounded independent review is complete."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.evaluation import (  # noqa: E402
    ReviewValidationError,
    apply_review_decisions,
    assert_group_disjoint,
    stable_grouped_split,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audited-qa", required=True, type=Path)
    parser.add_argument("--review-csv", required=True, type=Path)
    parser.add_argument("--children", required=True, type=Path)
    parser.add_argument("--review-requirements", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--development-fraction", type=float, default=0.4)
    parser.add_argument("--split-seed", default="aviation-rag-v1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    audited_path = args.audited_qa.resolve()
    review_path = args.review_csv.resolve()
    children_path = args.children.resolve()
    requirements_path = (
        args.review_requirements.resolve()
        if args.review_requirements
        else review_path.with_name("review_requirements.json")
    )
    output = args.output.resolve()

    candidate_records = read_jsonl(audited_path)
    if not requirements_path.exists():
        raise SystemExit(f"Missing review requirements manifest: {requirements_path}")
    requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
    expected_qa_ids = set(requirements.get("required_qa_ids", []))
    expected_count = requirements.get("expected_review_row_count")
    if expected_count != len(expected_qa_ids):
        raise SystemExit("Review requirements row count and QA-ID list disagree")
    requirement_inputs = requirements.get("inputs", {})
    actual_input_hashes = {
        "audited_qa_sha256": sha256(audited_path),
        "children_sha256": sha256(children_path),
    }
    mismatched_hashes = {
        name: {"expected": requirement_inputs.get(name), "actual": actual}
        for name, actual in actual_input_hashes.items()
        if requirement_inputs.get(name) != actual
    }
    if mismatched_hashes:
        raise SystemExit(f"Review requirements input hash mismatch: {mismatched_hashes}")

    child_by_id = {row["child_id"]: row for row in read_jsonl(children_path)}
    with review_path.open(encoding="utf-8-sig", newline="") as stream:
        review_rows = list(csv.DictReader(stream))

    try:
        retained, review_summary = apply_review_decisions(
            candidate_records,
            review_rows,
            child_by_id,
            expected_qa_ids,
        )
    except ReviewValidationError as error:
        raise SystemExit(str(error)) from error

    assignments = stable_grouped_split(
        retained,
        development_fraction=args.development_fraction,
        seed=args.split_seed,
    )
    assert_group_disjoint(retained, assignments)

    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    benchmark_path = output / "reviewed_benchmark.jsonl"
    benchmark_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in retained),
        encoding="utf-8",
    )
    decisions_path = output / "independent_review_decisions.csv"
    shutil.copyfile(review_path, decisions_path)

    split_rows = [
        {
            "qa_id": record["qa_id"],
            "parent_id": record["parent_id"],
            "split": assignments[record["qa_id"]],
            "audit_decision": record["audit_decision"],
            "independent_human_review": record["independent_human_review"],
        }
        for record in retained
    ]
    split_path = output / "split_manifest.csv"
    with split_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(split_rows[0]))
        writer.writeheader()
        writer.writerows(split_rows)

    split_counts = Counter(row["split"] for row in split_rows)
    parent_counts = Counter(
        (row["split"], row["parent_id"])
        for row in split_rows
    )
    summary = {
        **review_summary,
        "status": "frozen_reviewed_exceptions_and_stratified_sample",
        "benchmark_scope_note": (
            "All audit exceptions and a deterministic stratified unchanged sample were "
            "independently reviewed; unselected retained records were not individually reviewed."
        ),
        "split_seed": args.split_seed,
        "development_fraction_requested": args.development_fraction,
        "split_record_counts": dict(sorted(split_counts.items())),
        "split_parent_counts": {
            split: sum(
                1
                for candidate_split, _ in parent_counts
                if candidate_split == split
            )
            for split in ("development", "test")
        },
        "source_group_leakage_count": 0,
        "cached_question_embeddings_fully_reusable": not review_summary[
            "changed_question_qa_ids"
        ],
        "cached_rankings_require_recomputation": bool(
            review_summary["changed_question_qa_ids"]
        ),
    }
    summary_path = output / "freeze_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest = {
        "experiment_id": "reviewed_benchmark_freeze_v1",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "frozen_reviewed_exceptions_and_stratified_sample",
        "inputs": {
            "audited_qa_sha256": sha256(audited_path),
            "independent_review_csv_sha256": sha256(review_path),
            "children_sha256": sha256(children_path),
            "review_requirements_sha256": sha256(requirements_path),
        },
        "parameters": {
            "development_fraction": args.development_fraction,
            "split_seed": args.split_seed,
        },
        "outputs": {
            "reviewed_benchmark_sha256": sha256(benchmark_path),
            "review_decisions_copy_sha256": sha256(decisions_path),
            "split_manifest_sha256": sha256(split_path),
            "freeze_summary_sha256": sha256(summary_path),
        },
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

