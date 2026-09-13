"""Build deterministic evidence contexts from saved reranked candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.generation import ContextSelectionConfig, build_context_bundle  # noqa: E402


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


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reranked", required=True, type=Path)
    parser.add_argument("--children", required=True, type=Path)
    parser.add_argument("--parents", required=True, type=Path)
    parser.add_argument("--audited-qa", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-words", type=int, default=1200)
    parser.add_argument("--neighbor-radius", type=int, default=0)
    parser.add_argument("--max-per-parent", type=int)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    reranked_path = args.reranked.resolve()
    children_path = args.children.resolve()
    parents_path = args.parents.resolve()
    qa_path = args.audited_qa.resolve()
    ranking_rows = read_jsonl(reranked_path)
    children = {row["child_id"]: row for row in read_jsonl(children_path)}
    parents = {row["parent_id"]: row for row in read_jsonl(parents_path)}
    qa = {
        row["qa_id"]: row
        for row in read_jsonl(qa_path)
        if row["audit_decision"] != "excluded_invalid"
    }
    if set(qa) != {row["qa_id"] for row in ranking_rows}:
        raise SystemExit("Reranked candidates and audited QA contain different QA IDs")

    config = ContextSelectionConfig(
        top_k=args.top_k,
        max_words=args.max_words,
        neighbor_radius=args.neighbor_radius,
        max_per_parent=args.max_per_parent,
    )
    config.validate()
    output_rows: list[dict] = []
    for ranking_row in ranking_rows:
        qa_id = ranking_row["qa_id"]
        bundle = build_context_bundle(
            question=qa[qa_id]["question"],
            ranked_child_ids=[
                item["child_id"] for item in ranking_row["ranking"]
            ],
            children_by_id=children,
            parents_by_id=parents,
            config=config,
        )
        output_rows.append(
            {
                "qa_id": qa_id,
                "split": ranking_row["split"],
                **bundle,
            }
        )

    contexts_path = output / "contexts.jsonl"
    with contexts_path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in output_rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    words = [row["stats"]["evidence_words"] for row in output_rows]
    sources = [row["stats"]["source_count"] for row in output_rows]
    anchors = [row["stats"]["anchor_count"] for row in output_rows]
    neighbours = [row["stats"]["neighbor_count"] for row in output_rows]
    summary = {
        "query_count": len(output_rows),
        "configuration": {
            "top_k": args.top_k,
            "max_words": args.max_words,
            "neighbor_radius": args.neighbor_radius,
            "max_per_parent": args.max_per_parent,
        },
        "evidence_words": {
            "mean": statistics.mean(words),
            "median": statistics.median(words),
            "p95": percentile(words, 0.95),
            "maximum": max(words),
        },
        "source_count": {
            "mean": statistics.mean(sources),
            "median": statistics.median(sources),
            "p95": percentile(sources, 0.95),
            "maximum": max(sources),
        },
        "anchor_count_mean": statistics.mean(anchors),
        "neighbor_count_mean": statistics.mean(neighbours),
        "questions_with_budget_skips": sum(
            bool(row["stats"]["skipped_for_budget"]) for row in output_rows
        ),
    }
    summary_path = output / "context_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": "E5_candidate_context_assembly",
        "status": "candidate_contexts_no_generation_performed",
        "parameters": summary["configuration"],
        "query_count": len(output_rows),
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "inputs": {
            "reranked_sha256": sha256(reranked_path),
            "children_sha256": sha256(children_path),
            "parents_sha256": sha256(parents_path),
            "audited_qa_sha256": sha256(qa_path),
        },
        "outputs": {
            "contexts_sha256": sha256(contexts_path),
            "summary_sha256": sha256(summary_path),
        },
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
