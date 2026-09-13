"""Rerank a fixed hybrid candidate set with a local cross-encoder."""

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

from aviation_rag.retrieval import evaluate_rankings, rerank_from_scores  # noqa: E402


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


def score_pairs(
    questions: list[str],
    passages: list[str],
    *,
    model_name: str,
    batch_size: int,
    max_length: int,
) -> tuple[list[float], dict[str, str | bool]]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    scores: list[float] = []
    with torch.inference_mode():
        for start in range(0, len(questions), batch_size):
            stop = min(start + batch_size, len(questions))
            encoded = tokenizer(
                questions[start:stop],
                passages[start:stop],
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            encoded = {name: value.to(device) for name, value in encoded.items()}
            logits = model(**encoded).logits.reshape(-1)
            scores.extend(float(value) for value in logits.detach().cpu())
            print(f"scored={stop}/{len(questions)}", flush=True)

    metadata = {
        "device": str(device),
        "cuda": torch.cuda.is_available(),
        "torch": torch.__version__,
        "transformers_model_commit": str(
            getattr(model.config, "_commit_hash", "unknown")
        ),
    }
    return scores, metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hybrid-rankings", required=True, type=Path)
    parser.add_argument("--children", required=True, type=Path)
    parser.add_argument("--audited-qa", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--score-cache", required=True, type=Path)
    parser.add_argument(
        "--model",
        default="cross-encoder/ms-marco-MiniLM-L6-v2",
    )
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--refresh-scores", action="store_true")
    args = parser.parse_args()

    if args.candidate_k < 1 or args.batch_size < 1 or args.max_length < 1:
        raise SystemExit("candidate-k, batch-size, and max-length must be positive")

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    ranking_path = args.hybrid_rankings.resolve()
    children_path = args.children.resolve()
    qa_path = args.audited_qa.resolve()
    input_rows = read_jsonl(ranking_path)
    children = {row["child_id"]: row for row in read_jsonl(children_path)}
    qa = {
        row["qa_id"]: row
        for row in read_jsonl(qa_path)
        if row["audit_decision"] != "excluded_invalid"
    }
    if set(qa) != {row["qa_id"] for row in input_rows}:
        raise SystemExit("Hybrid rankings and audited QA contain different QA IDs")

    cache_metadata = {
        "model": args.model,
        "candidate_k": args.candidate_k,
        "max_length": args.max_length,
        "hybrid_rankings_sha256": sha256(ranking_path),
        "children_sha256": sha256(children_path),
        "audited_qa_sha256": sha256(qa_path),
    }
    score_cache = args.score_cache.resolve()
    cached = None
    if score_cache.exists() and not args.refresh_scores:
        candidate_cache = json.loads(score_cache.read_text(encoding="utf-8"))
        if candidate_cache.get("metadata") == cache_metadata:
            cached = candidate_cache

    model_runtime: dict[str, str | bool] = {}
    if cached is None:
        flat_questions: list[str] = []
        flat_passages: list[str] = []
        offsets: list[tuple[str, int, int]] = []
        for row in input_rows:
            candidates = row["ranking"][: args.candidate_k]
            start = len(flat_questions)
            flat_questions.extend([qa[row["qa_id"]]["question"]] * len(candidates))
            flat_passages.extend(
                children[item["child_id"]]["retrieval_text"] for item in candidates
            )
            offsets.append((row["qa_id"], start, len(candidates)))
        flat_scores, model_runtime = score_pairs(
            flat_questions,
            flat_passages,
            model_name=args.model,
            batch_size=args.batch_size,
            max_length=args.max_length,
        )
        scores_by_qa = {
            qa_id: flat_scores[start : start + count]
            for qa_id, start, count in offsets
        }
        score_cache.parent.mkdir(parents=True, exist_ok=True)
        score_cache.write_text(
            json.dumps(
                {
                    "metadata": cache_metadata,
                    "model_runtime": model_runtime,
                    "scores": scores_by_qa,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        cache_reused = False
    else:
        scores_by_qa = cached["scores"]
        model_runtime = cached.get("model_runtime", {})
        cache_reused = True

    output_rows: list[dict] = []
    rankings: dict[str, list[str]] = {}
    child_parent: dict[str, str] = {}
    qa_records: list[dict] = []
    for row in input_rows:
        qa_id = row["qa_id"]
        candidates = row["ranking"][: args.candidate_k]
        candidate_ids = [item["child_id"] for item in candidates]
        reranked = rerank_from_scores(
            candidate_ids,
            scores_by_qa[qa_id],
            limit=args.candidate_k,
        )
        parent_by_child = {
            item["child_id"]: item["parent_id"] for item in candidates
        }
        rankings[qa_id] = [child_id for child_id, _, _ in reranked]
        child_parent.update(parent_by_child)
        qa_records.append(
            {
                "qa_id": qa_id,
                "parent_id": row["gold_parent_id"],
                "gold_child_ids": row["gold_child_ids"],
                "split": row["split"],
            }
        )
        output_rows.append(
            {
                "qa_id": qa_id,
                "split": row["split"],
                "gold_parent_id": row["gold_parent_id"],
                "gold_child_ids": row["gold_child_ids"],
                "ranking": [
                    {
                        "rank": rank,
                        "child_id": child_id,
                        "parent_id": parent_by_child[child_id],
                        "score": round(score, 8),
                        "hybrid_original_rank": original_rank,
                    }
                    for rank, (child_id, score, original_rank) in enumerate(
                        reranked, start=1
                    )
                ],
            }
        )

    k_values = [value for value in (1, 3, 5, 10, 20) if value <= args.candidate_k]
    metrics: dict[str, dict] = {}
    for split in ("development", "test", "all"):
        split_records = (
            qa_records
            if split == "all"
            else [record for record in qa_records if record["split"] == split]
        )
        metrics[split] = evaluate_rankings(
            split_records,
            rankings,
            child_parent,
            k_values,
        )

    output_rankings = output / "rankings.jsonl"
    with output_rankings.open("w", encoding="utf-8", newline="\n") as stream:
        for row in output_rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    metrics_path = output / "retrieval_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": "E4_cross_encoder_rerank_candidate",
        "status": "candidate_evaluation_independent_human_review_pending",
        "parameters": {
            "model": args.model,
            "candidate_k": args.candidate_k,
            "max_length": args.max_length,
            "batch_size": args.batch_size,
        },
        "cache": {
            "scores_reused": cache_reused,
            "score_cache_sha256": sha256(score_cache),
        },
        "query_count": len(qa_records),
        "pair_count": sum(
            min(args.candidate_k, len(row["ranking"])) for row in input_rows
        ),
        "model_runtime": model_runtime,
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "inputs": cache_metadata,
        "outputs": {
            "rankings_sha256": sha256(output_rankings),
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
