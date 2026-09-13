"""Run a fully local BM25 retrieval evaluation over the E1 child corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.retrieval import BM25Index, evaluate_rankings  # noqa: E402


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--children", required=True, type=Path)
    parser.add_argument("--audited-qa", required=True, type=Path)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--k1", type=float, default=1.5)
    parser.add_argument("--b", type=float, default=0.75)
    parser.add_argument("--max-k", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    children_path = args.children.resolve()
    qa_path = args.audited_qa.resolve()
    split_path = args.split_manifest.resolve()
    children = read_jsonl(children_path)
    qa_records = [
        record
        for record in read_jsonl(qa_path)
        if record["audit_decision"] != "excluded_invalid"
    ]
    split_rows = read_csv(split_path)
    split_by_qa = {row["qa_id"]: row["split"] for row in split_rows}
    if set(split_by_qa) != {record["qa_id"] for record in qa_records}:
        raise SystemExit("Split manifest QA IDs do not match retained audited QA")

    child_ids = [child["child_id"] for child in children]
    index = BM25Index(
        [child["retrieval_text"] for child in children],
        child_ids,
        k1=args.k1,
        b=args.b,
    )
    ranked = [
        index.rank(record["question"], args.max_k)
        for record in qa_records
    ]
    rankings = {
        record["qa_id"]: [child_id for child_id, _ in ranking]
        for record, ranking in zip(qa_records, ranked)
    }
    child_parent = {child["child_id"]: child["parent_id"] for child in children}
    k_values = [value for value in (1, 3, 5, 10, 20) if value <= args.max_k]
    metrics: dict[str, dict] = {}
    for split in ("development", "test", "all"):
        split_records = (
            qa_records
            if split == "all"
            else [
                record
                for record in qa_records
                if split_by_qa[record["qa_id"]] == split
            ]
        )
        metrics[split] = evaluate_rankings(
            split_records,
            rankings,
            child_parent,
            k_values,
        )

    ranking_path = output / "rankings.jsonl"
    with ranking_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record, ranking in zip(qa_records, ranked):
            stream.write(
                json.dumps(
                    {
                        "qa_id": record["qa_id"],
                        "split": split_by_qa[record["qa_id"]],
                        "gold_parent_id": record["parent_id"],
                        "gold_child_ids": record["gold_child_ids"],
                        "ranking": [
                            {
                                "rank": rank,
                                "child_id": child_id,
                                "parent_id": child_parent[child_id],
                                "score": round(score, 8),
                            }
                            for rank, (child_id, score) in enumerate(ranking, start=1)
                        ],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    metrics_path = output / "retrieval_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": "BM25_local_candidate",
        "status": "candidate_evaluation_independent_human_review_pending",
        "parameters": {"k1": args.k1, "b": args.b},
        "maximum_rank": args.max_k,
        "corpus_count": len(children),
        "query_count": len(qa_records),
        "software": {"python": sys.version, "platform": platform.platform()},
        "inputs": {
            "children_sha256": sha256(children_path),
            "audited_qa_sha256": sha256(qa_path),
            "split_manifest_sha256": sha256(split_path),
        },
        "outputs": {
            "rankings_sha256": sha256(ranking_path),
            "metrics_sha256": sha256(metrics_path),
        },
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
