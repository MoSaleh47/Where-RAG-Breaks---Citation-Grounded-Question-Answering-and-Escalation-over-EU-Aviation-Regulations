"""Map legacy QA source chunks to the validated E1 parent corpus."""

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

from aviation_rag.evaluation import map_legacy_chunks  # noqa: E402


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


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-chunks", required=True, type=Path)
    parser.add_argument("--qa", required=True, type=Path)
    parser.add_argument("--parents", required=True, type=Path)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    chunk_path = args.legacy_chunks.resolve()
    qa_path = args.qa.resolve()
    parent_path = args.parents.resolve()
    legacy_chunks = read_csv(chunk_path)
    qa_records = json.loads(qa_path.read_text(encoding="utf-8"))
    parents = read_jsonl(parent_path)
    parent_by_id = {parent["parent_id"]: parent for parent in parents}

    chunk_mappings = map_legacy_chunks(legacy_chunks, parents)
    mapping_by_chunk = {
        mapping["legacy_chunk_id"]: mapping for mapping in chunk_mappings
    }
    qa_counts = Counter(record["source_chunk"] for record in qa_records)
    for mapping in chunk_mappings:
        mapping["qa_count"] = qa_counts[mapping["legacy_chunk_id"]]

    overrides: dict[str, dict] = {}
    override_path = args.overrides.resolve() if args.overrides else None
    if override_path:
        overrides = {row["qa_id"]: row for row in read_csv(override_path)}
        unknown = sorted(set(overrides) - {record["qa_id"] for record in qa_records})
        if unknown:
            raise SystemExit(f"Overrides contain unknown QA IDs: {unknown}")

    qa_mappings: list[dict] = []
    for qa in qa_records:
        mapping = mapping_by_chunk[qa["source_chunk"]]
        parent_id = mapping["parent_id"]
        status = mapping["mapping_status"]
        method = mapping["mapping_method"]
        review_note = ""

        override = overrides.get(qa["qa_id"])
        if override:
            decision = override["decision"]
            parent_id = override.get("parent_id", "").strip() or parent_id
            review_note = override.get("review_note", "")
            if decision == "accept":
                status, method = "accepted_manual", "qa_override"
            elif decision == "rewrite":
                status, method = "rewrite_required", "qa_override"
            elif decision == "exclude":
                status, method = "excluded_invalid_source", "qa_override"
            else:
                raise SystemExit(
                    f"Unsupported override decision for {qa['qa_id']}: {decision}"
                )

        if parent_id not in parent_by_id:
            raise SystemExit(f"Unknown mapped parent ID for {qa['qa_id']}: {parent_id}")
        parent = parent_by_id[parent_id]
        qa_mappings.append(
            {
                "qa_id": qa["qa_id"],
                "legacy_source_chunk": qa["source_chunk"],
                "gold_citation": qa.get("citation", ""),
                "parent_id": parent_id,
                "parent_canonical_citation": parent["canonical_citation"],
                "mapping_status": status,
                "mapping_method": method,
                "match_score": mapping["match_score"],
                "source_token_coverage": mapping["source_token_coverage"],
                "review_note": review_note,
            }
        )

    chunk_fields = [
        "legacy_chunk_id",
        "legacy_citation",
        "legacy_type",
        "qa_count",
        "mapping_status",
        "mapping_method",
        "parent_id",
        "parent_canonical_citation",
        "match_score",
        "cosine_similarity",
        "source_token_coverage",
        "score_margin",
        "candidate_parent_ids",
    ]
    qa_fields = [
        "qa_id",
        "legacy_source_chunk",
        "gold_citation",
        "parent_id",
        "parent_canonical_citation",
        "mapping_status",
        "mapping_method",
        "match_score",
        "source_token_coverage",
        "review_note",
    ]
    chunk_output = output / "legacy_chunk_parent_map.csv"
    qa_output = output / "qa_parent_map.csv"
    write_csv(chunk_output, chunk_mappings, chunk_fields)
    write_csv(qa_output, qa_mappings, qa_fields)

    summary = {
        "legacy_chunk_count": len(legacy_chunks),
        "qa_count": len(qa_records),
        "chunk_status_counts": dict(
            sorted(Counter(row["mapping_status"] for row in chunk_mappings).items())
        ),
        "qa_status_counts": dict(
            sorted(Counter(row["mapping_status"] for row in qa_mappings).items())
        ),
        "inputs": {
            "legacy_chunks_sha256": sha256(chunk_path),
            "qa_sha256": sha256(qa_path),
            "parents_sha256": sha256(parent_path),
            "overrides_sha256": sha256(override_path) if override_path else None,
        },
        "outputs": {
            "legacy_chunk_parent_map_sha256": sha256(chunk_output),
            "qa_parent_map_sha256": sha256(qa_output),
        },
    }
    (output / "mapping_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
