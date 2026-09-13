"""Fuse two saved retrieval runs and evaluate the hybrid ranking."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.retrieval import evaluate_rankings, reciprocal_rank_fusion  # noqa: E402


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
    parser.add_argument("--dense-rankings", required=True, type=Path)
    parser.add_argument("--lexical-rankings", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rrf-constant", type=int, default=60)
    parser.add_argument("--max-k", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    dense_path = args.dense_rankings.resolve()
    lexical_path = args.lexical_rankings.resolve()
    dense_rows = {row["qa_id"]: row for row in read_jsonl(dense_path)}
    lexical_rows = {row["qa_id"]: row for row in read_jsonl(lexical_path)}
    if set(dense_rows) != set(lexical_rows):
        raise SystemExit("Dense and lexical rankings contain different QA IDs")

    fused_rows: list[dict] = []
    rankings: dict[str, list[str]] = {}
    child_parent: dict[str, str] = {}
    qa_records: list[dict] = []
    for qa_id, dense_row in dense_rows.items():
        lexical_row = lexical_rows[qa_id]
        for field in ("split", "gold_parent_id", "gold_child_ids"):
            if dense_row[field] != lexical_row[field]:
                raise SystemExit(f"Input mismatch for {qa_id}: {field}")
        dense_ids = [item["child_id"] for item in dense_row["ranking"]]
        lexical_ids = [item["child_id"] for item in lexical_row["ranking"]]
        fused = reciprocal_rank_fusion(
            [dense_ids, lexical_ids],
            constant=args.rrf_constant,
            limit=args.max_k,
        )
        parent_lookup = {
            item["child_id"]: item["parent_id"]
            for item in dense_row["ranking"] + lexical_row["ranking"]
        }
        fused_ids = [child_id for child_id, _ in fused]
        rankings[qa_id] = fused_ids
        child_parent.update(
            {child_id: parent_lookup[child_id] for child_id in fused_ids}
        )
        qa_records.append(
            {
                "qa_id": qa_id,
                "parent_id": dense_row["gold_parent_id"],
                "gold_child_ids": dense_row["gold_child_ids"],
                "split": dense_row["split"],
            }
        )
        fused_rows.append(
            {
                "qa_id": qa_id,
                "split": dense_row["split"],
                "gold_parent_id": dense_row["gold_parent_id"],
                "gold_child_ids": dense_row["gold_child_ids"],
                "ranking": [
                    {
                        "rank": rank,
                        "child_id": child_id,
                        "parent_id": parent_lookup[child_id],
                        "score": round(score, 10),
                    }
                    for rank, (child_id, score) in enumerate(fused, start=1)
                ],
            }
        )

    k_values = [value for value in (1, 3, 5, 10, 20) if value <= args.max_k]
    metrics: dict[str, dict] = {}
    for split in ("development", "test", "all"):
        split_records = (
            qa_records
            if split == "all"
            else [record for record in qa_records if record["split"] == split]
        )
        metrics[split] = evaluate_rankings(
            split_records, rankings, child_parent, k_values
        )

    ranking_path = output / "rankings.jsonl"
    with ranking_path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in fused_rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    metrics_path = output / "retrieval_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "experiment_id": "E3_hybrid_rrf_candidate",
        "status": "candidate_evaluation_independent_human_review_pending",
        "parameters": {
            "method": "equal_weight_reciprocal_rank_fusion",
            "rrf_constant": args.rrf_constant,
        },
        "maximum_rank": args.max_k,
        "query_count": len(qa_records),
        "software": {"python": sys.version, "platform": platform.platform()},
        "inputs": {
            "dense_rankings_sha256": sha256(dense_path),
            "lexical_rankings_sha256": sha256(lexical_path),
        },
        "outputs": {
            "rankings_sha256": sha256(ranking_path),
            "metrics_sha256": sha256(metrics_path),
        },
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
