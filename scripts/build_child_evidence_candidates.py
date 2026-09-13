"""Build a human-review queue of candidate E1 child evidence for legacy QA."""

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

from aviation_rag.evaluation import rank_child_candidates, review_priority  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa", required=True, type=Path)
    parser.add_argument("--qa-parent-map", required=True, type=Path)
    parser.add_argument("--children", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    qa_path = args.qa.resolve()
    mapping_path = args.qa_parent_map.resolve()
    children_path = args.children.resolve()
    qa_records = json.loads(qa_path.read_text(encoding="utf-8"))
    qa_by_id = {record["qa_id"]: record for record in qa_records}
    mappings = read_csv(mapping_path)
    children = read_jsonl(children_path)
    rows: list[dict] = []

    for mapping in mappings:
        qa = qa_by_id[mapping["qa_id"]]
        mapping_status = mapping["mapping_status"]
        if mapping_status in {"excluded_invalid_source", "rewrite_required"}:
            candidates: list[dict] = []
            priority = "excluded" if mapping_status.startswith("excluded") else "rewrite"
        else:
            candidates = rank_child_candidates(qa, mapping["parent_id"], children)
            priority = review_priority(candidates)

        top_score = candidates[0]["score"] if candidates else ""
        second_score = candidates[1]["score"] if len(candidates) > 1 else ""
        row = {
            "qa_id": qa["qa_id"],
            "question": qa["question"],
            "reference_answer": qa["answer"],
            "gold_citation": qa.get("citation", ""),
            "parent_id": mapping["parent_id"],
            "parent_mapping_status": mapping_status,
            "review_priority": priority,
            "top_score": top_score,
            "score_margin": (
                round(top_score - second_score, 6)
                if isinstance(top_score, float) and isinstance(second_score, float)
                else ""
            ),
            "candidate_child_ids": ";".join(item["child_id"] for item in candidates),
            "candidate_citations": ";".join(
                item["canonical_citation"] for item in candidates
            ),
            "candidate_scores": ";".join(str(item["score"]) for item in candidates),
            "top_evidence_preview": candidates[0]["text_preview"] if candidates else "",
            "review_decision": "",
            "gold_child_ids": "",
            "answer_support": "",
            "review_notes": mapping.get("review_note", ""),
        }
        rows.append(row)

    fields = list(rows[0])
    queue_path = output / "qa_child_evidence_review.csv"
    with queue_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "qa_count": len(rows),
        "review_priority_counts": dict(
            sorted(Counter(row["review_priority"] for row in rows).items())
        ),
        "parent_mapping_status_counts": dict(
            sorted(Counter(row["parent_mapping_status"] for row in rows).items())
        ),
        "inputs": {
            "qa_sha256": sha256(qa_path),
            "qa_parent_map_sha256": sha256(mapping_path),
            "children_sha256": sha256(children_path),
        },
        "output_sha256": sha256(queue_path),
        "status": "candidate_queue_only_human_review_required",
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
