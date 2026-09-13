"""Run a cached dense-retrieval experiment over the E1 child corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI, __version__ as openai_version

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.retrieval import dense_rank, evaluate_rankings  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def text_digest(values: list[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
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


def embed_texts(
    client: OpenAI,
    texts: list[str],
    model: str,
    batch_size: int,
) -> tuple[np.ndarray, int]:
    vectors: list[list[float]] = []
    input_tokens = 0
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = client.embeddings.create(
            model=model,
            input=batch,
            encoding_format="float",
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors.extend(item.embedding for item in ordered)
        if response.usage is not None:
            input_tokens += response.usage.prompt_tokens
        print(f"embedded={min(start + batch_size, len(texts))}/{len(texts)}")
    return np.asarray(vectors, dtype=np.float32), input_tokens


def cached_embeddings(
    client: OpenAI,
    cache_path: Path,
    metadata_path: Path,
    texts: list[str],
    ids: list[str],
    model: str,
    batch_size: int,
) -> tuple[np.ndarray, int, bool]:
    expected = {
        "model": model,
        "count": len(texts),
        "ids_sha256": text_digest(ids),
        "texts_sha256": text_digest(texts),
    }
    if cache_path.exists() and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if all(metadata.get(key) == value for key, value in expected.items()):
            embeddings = np.load(cache_path)
            if embeddings.shape[0] != len(texts):
                raise ValueError(f"Invalid cached embedding count: {cache_path}")
            return embeddings, 0, True

    embeddings, input_tokens = embed_texts(client, texts, model, batch_size)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, embeddings)
    metadata = {
        **expected,
        "shape": list(embeddings.shape),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_tokens": input_tokens,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return embeddings, input_tokens, False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--children", required=True, type=Path)
    parser.add_argument("--audited-qa", required=True, type=Path)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--max-k", type=int, default=20)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)

    load_dotenv(WORKSPACE_ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not configured")
    client = OpenAI()

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
    child_texts = [child["retrieval_text"] for child in children]
    questions = [record["question"] for record in qa_records]
    qa_ids = [record["qa_id"] for record in qa_records]

    corpus_vectors, corpus_tokens, corpus_cached = cached_embeddings(
        client,
        cache / f"{args.model}_children.npy",
        cache / f"{args.model}_children.json",
        child_texts,
        child_ids,
        args.model,
        args.batch_size,
    )
    query_vectors, query_tokens, query_cached = cached_embeddings(
        client,
        cache / f"{args.model}_legacy100_queries.npy",
        cache / f"{args.model}_legacy100_queries.json",
        questions,
        qa_ids,
        args.model,
        args.batch_size,
    )

    ranked = dense_rank(
        query_vectors,
        corpus_vectors,
        child_ids,
        args.max_k,
    )
    rankings = {
        qa_id: [child_id for child_id, _ in ranking]
        for qa_id, ranking in zip(qa_ids, ranked)
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
        "experiment_id": "E1_dense_candidate",
        "status": "candidate_evaluation_independent_human_review_pending",
        "model": args.model,
        "embedding_dimensions": int(corpus_vectors.shape[1]),
        "maximum_rank": args.max_k,
        "corpus_count": len(children),
        "query_count": len(qa_records),
        "api_input_tokens_this_run": corpus_tokens + query_tokens,
        "cache": {
            "corpus_reused": corpus_cached,
            "queries_reused": query_cached,
        },
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "openai": openai_version,
            "numpy": np.__version__,
        },
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
