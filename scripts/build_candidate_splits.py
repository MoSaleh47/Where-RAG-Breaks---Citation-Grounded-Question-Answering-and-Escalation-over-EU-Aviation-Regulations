"""Build deterministic source-grouped manifests from an audited QA candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.evaluation import assert_group_disjoint, stable_grouped_split  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audited-qa", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--development-fraction", type=float, default=0.4)
    parser.add_argument("--seed", default="aviation-rag-v1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    input_path = args.audited_qa.resolve()
    all_records = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = [
        record
        for record in all_records
        if record["audit_decision"] != "excluded_invalid"
    ]
    assignments = stable_grouped_split(
        records,
        development_fraction=args.development_fraction,
        seed=args.seed,
    )
    assert_group_disjoint(records, assignments)

    rows = [
        {
            "qa_id": record["qa_id"],
            "parent_id": record["parent_id"],
            "split": assignments[record["qa_id"]],
            "audit_decision": record["audit_decision"],
            "independent_human_review": record["independent_human_review"],
        }
        for record in records
    ]
    manifest_path = output / "split_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    split_counts = Counter(row["split"] for row in rows)
    parent_counts = Counter(
        (row["split"], row["parent_id"])
        for row in rows
    )
    summary = {
        "status": "candidate_not_final_gold",
        "seed": args.seed,
        "development_fraction_requested": args.development_fraction,
        "record_counts": dict(sorted(split_counts.items())),
        "parent_counts": {
            split: sum(1 for candidate_split, _ in parent_counts if candidate_split == split)
            for split in ("development", "test")
        },
        "source_group_leakage_count": 0,
        "independent_human_review_complete": all(
            record["independent_human_review"] for record in records
        ),
        "input_sha256": sha256(input_path),
        "manifest_sha256": sha256(manifest_path),
    }
    (output / "split_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
