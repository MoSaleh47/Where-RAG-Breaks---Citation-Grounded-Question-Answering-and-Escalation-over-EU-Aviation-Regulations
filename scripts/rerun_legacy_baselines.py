"""Re-run the historical few-shot and RAG baselines over the frozen benchmark.

Why this exists
---------------
The stored predictions in ``Documents/results_*.json`` answer the *pre-freeze*
wording of the questions. Twenty-five of the 98 frozen records were reworded --
eight during the independent review and seventeen earlier by the AI audit -- so
``rescore_legacy_baselines.py`` drops them, and the three-system comparison in
Chapter 5 covers 73 records rather than 98. The excluded records are not a
random subset: they are the ones judged vague or compound, so the surviving 73
are plausibly the better-posed part of the benchmark.

This script regenerates the few-shot and RAG predictions over all 98 frozen
records, using the frozen question wording, so that the comparison can be
reported over the whole benchmark under one provenance.

What is held identical to the historical run
--------------------------------------------
* the system prompts, verbatim from ``run_fewshot.py`` and ``run_rag.py``;
* the exemplar-sampling procedure (seed 42, reset per k, k exemplars drawn from
  the full historical pool excluding the question being asked);
* temperature 0.0 and the same ``max_tokens`` per system;
* the legacy flat chunk index (``Documents/regulation_chunks_clean.csv``) with
  the same 150-character floor, the same ``text[:1500]`` context truncation and
  the same k values.

What differs, and is recorded rather than hidden
------------------------------------------------
* The model is pinned to a dated snapshot instead of the floating ``gpt-4o-mini``
  alias, so the run cannot silently change model underneath the comparison. The
  default matches the snapshot the historical run resolved to.
* Retrieval uses NumPy cosine similarity over L2-normalised vectors rather than
  ``faiss.IndexFlatIP``. These compute the same quantity; the substitution
  removes a native dependency. Ties are broken by chunk order, so the ranking is
  deterministic.
* The question set is the 98 frozen records, iterated in the order of the
  historical seeded sample, not the historical 100.

Nothing under ``Documents/`` is modified: the historical artefacts stay
immutable (decision D002) and the new predictions are written to their own
experiment directory.

Usage (from ``aviation_rag_research/``)::

    python scripts/rerun_legacy_baselines.py \
        --benchmark data/evaluation/reviewed_benchmark_v1/reviewed_benchmark.jsonl \
        --qa-pairs ../Documents/qa_pairs_final.json \
        --chunks ../Documents/regulation_chunks_clean.csv \
        --output experiments/legacy_rerun_frozen98_v1 \
        --cache experiments/cache/legacy_rerun \
        --dry-run

Drop ``--dry-run`` to make the calls. Every response is cached by a digest over
model, system prompt and user prompt, so an interrupted run resumes without
paying twice and a repeat run costs nothing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------- constants --
# Copied verbatim from run_fewshot.py.
FEWSHOT_SYSTEM_PROMPT = """You are an expert assistant in EU aviation regulation.
Answer the question based on your knowledge of Regulation (EU) No 376/2014 
and EASA Easy Access Rules for Occurrence Reporting.

Your answer MUST:
1. Be concise (2-4 sentences)
2. End with an explicit citation in brackets, e.g. [Article 4(6)] or [Article 16(9)]
3. Be factually grounded — do not guess or hallucinate article numbers

Format:
Answer: <your answer here> [Citation]"""

# Copied verbatim from run_rag.py.
RAG_SYSTEM_PROMPT = """You are an expert assistant in EU aviation regulation.
You will be given one or more excerpts from Regulation (EU) No 376/2014 
and EASA Easy Access Rules for Occurrence Reporting.

Answer the question using ONLY the provided excerpts.
Your answer MUST:
1. Be concise (2-4 sentences)
2. Be strictly grounded in the provided text — do not add external knowledge
3. End with an explicit citation in brackets, e.g. [Article 4(6)] or [Article 16(9)]
4. If the answer is not found in the excerpts, say: "Not found in retrieved context."

Format:
Answer: <your answer> [Citation]"""

K_SHOTS = (1, 5, 10)
TOP_K_VALUES = (1, 3, 5)
RANDOM_SEED = 42
HISTORICAL_SAMPLE_SIZE = 100
MIN_CHUNK_CHARS = 150
CHUNK_TRUNCATION = 1500
FEWSHOT_MAX_TOKENS = 300
RAG_MAX_TOKENS = 350
TEMPERATURE = 0.0

# USD per million tokens, for the estimate only. The billed figure is whatever
# the provider's usage export says; this is a planning number.
PRICE_PER_MTOK = {
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}


# ------------------------------------------------------------------ helpers --
def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def estimate_tokens(text: str) -> int:
    """Rough token estimate; exact accounting comes from the API usage field."""
    return max(1, len(text) // 4)


class ResponseCache:
    """One JSON file per request digest. Resumable, and never re-bills."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    def key(self, *parts: str) -> str:
        return sha256_text("\x00".join(parts))

    def get(self, key: str) -> dict | None:
        path = self.directory / f"{key}.json"
        if path.exists():
            self.hits += 1
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def put(self, key: str, payload: dict) -> None:
        self.misses += 1
        (self.directory / f"{key}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ------------------------------------------------------------- data loading --
def load_records(benchmark: Path, qa_pairs: Path) -> tuple[list[dict], list[dict]]:
    """Frozen records in historical sample order, plus the exemplar pool."""
    frozen = {record["qa_id"]: record for record in read_jsonl(benchmark)}
    pool = json.loads(qa_pairs.read_text(encoding="utf-8"))

    # The historical scripts drew a fixed 100-question sample with seed 42 and
    # iterated it in that order. Preserving the order keeps the exemplar draw
    # sequence as close to the historical run as a changed record set allows.
    ordered_ids = [item["qa_id"] for item in random.Random(RANDOM_SEED).sample(pool, HISTORICAL_SAMPLE_SIZE)]
    ordered = [frozen[qa_id] for qa_id in ordered_ids if qa_id in frozen]

    missing = set(frozen) - set(ordered_ids)
    if missing:
        # Frozen records outside the historical sample would have no stored
        # counterpart at all; append them so the run still covers the benchmark.
        ordered.extend(frozen[qa_id] for qa_id in sorted(missing))
    return ordered, pool


def load_chunks(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return [
            row
            for row in csv.DictReader(stream)
            if int(row["char_count"]) >= MIN_CHUNK_CHARS
        ]


# ---------------------------------------------------------------- prompting --
def build_fewshot_prompt(examples: list[dict], question: str) -> str:
    shots = ""
    for example in examples:
        shots += f"Q: {example['question']}\nA: {example['answer']} [{example['citation']}]\n\n"
    shots += f"Q: {question}\nA:"
    return shots


def build_rag_context(retrieved: list[tuple[dict, float]]) -> str:
    parts = [
        f"[SOURCE: {chunk['citation']} | type: {chunk['type']}]\n{chunk['text'][:CHUNK_TRUNCATION]}"
        for chunk, _ in retrieved
    ]
    return "\n\n---\n\n".join(parts)


def build_rag_prompt(question: str, retrieved: list[tuple[dict, float]]) -> str:
    return f"""REGULATORY EXCERPTS:
{build_rag_context(retrieved)}

QUESTION: {question}

Answer:"""


# ------------------------------------------------------------------ the run --
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--qa-pairs", required=True, type=Path)
    parser.add_argument("--chunks", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18")
    parser.add_argument("--embed-model", default="text-embedding-3-small")
    parser.add_argument(
        "--only",
        choices=("fewshot", "rag", "both"),
        default="both",
        help="Run one system only. Both by default.",
    )
    parser.add_argument("--limit", type=int, help="First N records only (smoke test).")
    parser.add_argument("--dry-run", action="store_true", help="Build every request, call nothing.")
    parser.add_argument("--force", action="store_true", help="Overwrite a non-empty output directory.")
    parser.add_argument("--sleep", type=float, default=0.3)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force and not args.dry_run:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")

    records, pool = load_records(args.benchmark.resolve(), args.qa_pairs.resolve())
    if args.limit:
        records = records[: args.limit]
    chunks = load_chunks(args.chunks.resolve())
    pool_by_id = {item["qa_id"]: item for item in pool}

    print(f"Frozen records to answer : {len(records)}")
    print(f"Exemplar pool            : {len(pool)}")
    print(f"Legacy chunks indexed    : {len(chunks)} (>= {MIN_CHUNK_CHARS} chars)")
    print(f"Model                    : {args.model}")
    print(f"Mode                     : {'DRY RUN, nothing is called' if args.dry_run else 'LIVE'}")
    print()

    cache = ResponseCache(args.cache.resolve())
    usage = {"input_tokens": 0, "output_tokens": 0, "embedding_tokens": 0, "calls": 0}
    estimated = {"input_tokens": 0, "output_tokens": 0, "embedding_tokens": 0, "calls": 0}

    client = None
    if not args.dry_run:
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError:
            raise SystemExit(
                "The 'openai' package is not importable by this interpreter.\n"
                f"  interpreter: {sys.executable}\n"
                "Install it there, or run the same command with the interpreter that has it."
            )
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            env_file = Path(".env")
            if not env_file.exists():
                env_file = Path("..") / ".env"
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("OPENAI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if not api_key:
            raise SystemExit("OPENAI_API_KEY is not set and no .env file supplied one.")
        client = OpenAI(api_key=api_key)

    def chat(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        key = cache.key("chat", args.model, str(TEMPERATURE), str(max_tokens), system_prompt, user_prompt)
        hit = cache.get(key)
        if hit is not None:
            usage["input_tokens"] += hit.get("input_tokens", 0)
            usage["output_tokens"] += hit.get("output_tokens", 0)
            return hit["text"]
        estimated["calls"] += 1
        estimated["input_tokens"] += estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
        estimated["output_tokens"] += max_tokens // 2
        if args.dry_run:
            return ""
        response = client.chat.completions.create(
            model=args.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
        )
        text = (response.choices[0].message.content or "").strip()
        payload = {
            "text": text,
            "model_resolved": response.model,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
        cache.put(key, payload)
        usage["input_tokens"] += payload["input_tokens"]
        usage["output_tokens"] += payload["output_tokens"]
        usage["calls"] += 1
        time.sleep(args.sleep)
        return text

    def embed(texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        pending: list[tuple[int, str]] = []
        for index, text in enumerate(texts):
            key = cache.key("embed", args.embed_model, text)
            hit = cache.get(key)
            if hit is None:
                pending.append((index, text))
                vectors.append([])
            else:
                usage["embedding_tokens"] += hit.get("input_tokens", 0)
                vectors.append(hit["vector"])
        for start in range(0, len(pending), 50):
            batch = pending[start : start + 50]
            estimated["calls"] += 1
            estimated["embedding_tokens"] += sum(estimate_tokens(text) for _, text in batch)
            if args.dry_run:
                continue
            response = client.embeddings.create(
                model=args.embed_model, input=[text for _, text in batch]
            )
            per_item = response.usage.prompt_tokens // max(1, len(batch))
            for (index, text), item in zip(batch, response.data):
                cache.put(
                    cache.key("embed", args.embed_model, text),
                    {"vector": item.embedding, "input_tokens": per_item},
                )
                vectors[index] = item.embedding
            usage["embedding_tokens"] += response.usage.prompt_tokens
            usage["calls"] += 1
            time.sleep(args.sleep)
        return vectors

    results_fewshot: list[dict] = []
    results_rag: list[dict] = []

    # ---------------------------------------------------------- few-shot --
    if args.only in ("fewshot", "both"):
        for k in K_SHOTS:
            print(f"few-shot k={k}")
            rng = random.Random(RANDOM_SEED)
            for record in records:
                candidates = [item for item in pool if item["qa_id"] != record["qa_id"]]
                examples = rng.sample(candidates, min(k, len(candidates)))
                prediction = chat(
                    FEWSHOT_SYSTEM_PROMPT,
                    build_fewshot_prompt(examples, record["question"]),
                    FEWSHOT_MAX_TOKENS,
                )
                legacy = pool_by_id.get(record["qa_id"], {})
                results_fewshot.append(
                    {
                        "qa_id": record["qa_id"],
                        "k_shots": k,
                        "question": record["question"],
                        "question_type": record.get("question_type", ""),
                        "difficulty": record.get("difficulty", ""),
                        "gold_answer": record.get("reference_answer", ""),
                        "gold_citation": record.get("acceptable_citation", ""),
                        "gold_text": legacy.get("gold_text", ""),
                        "prediction": prediction,
                    }
                )

    # --------------------------------------------------------------- RAG --
    if args.only in ("rag", "both"):
        print("embedding legacy chunks")
        chunk_vectors = embed([chunk["text"] for chunk in chunks])
        print("embedding questions")
        question_vectors = embed([record["question"] for record in records])

        matrix = None
        if not args.dry_run:
            import numpy as np  # noqa: PLC0415

            matrix = np.asarray(chunk_vectors, dtype="float32")
            matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)

        for k in TOP_K_VALUES:
            print(f"RAG k={k}")
            for position, record in enumerate(records):
                if args.dry_run:
                    retrieved = [(chunk, 0.0) for chunk in chunks[:k]]
                else:
                    import numpy as np  # noqa: PLC0415

                    query = np.asarray(question_vectors[position], dtype="float32")
                    query /= np.linalg.norm(query)
                    scores = matrix @ query
                    # Descending score, ties broken by chunk order, as faiss does.
                    order = sorted(range(len(chunks)), key=lambda i: (-float(scores[i]), i))[:k]
                    retrieved = [(chunks[i], float(scores[i])) for i in order]

                prediction = chat(
                    RAG_SYSTEM_PROMPT,
                    build_rag_prompt(record["question"], retrieved),
                    RAG_MAX_TOKENS,
                )
                retrieved_ids = [chunk["chunk_id"] for chunk, _ in retrieved]
                legacy = pool_by_id.get(record["qa_id"], {})
                results_rag.append(
                    {
                        "qa_id": record["qa_id"],
                        "k": k,
                        "question": record["question"],
                        "question_type": record.get("question_type", ""),
                        "difficulty": record.get("difficulty", ""),
                        "gold_answer": record.get("reference_answer", ""),
                        "gold_citation": record.get("acceptable_citation", ""),
                        "gold_source_chunk": record.get("legacy_source_chunk", ""),
                        "gold_text": legacy.get("gold_text", ""),
                        "prediction": prediction,
                        "retrieved_chunks": json.dumps(
                            [
                                {
                                    "chunk_id": chunk["chunk_id"],
                                    "citation": chunk["citation"],
                                    "score": round(score, 4),
                                }
                                for chunk, score in retrieved
                            ]
                        ),
                        "retrieval_success": int(
                            record.get("legacy_source_chunk", "") in retrieved_ids
                        ),
                    }
                )

    # ------------------------------------------------------------ report --
    chat_price = PRICE_PER_MTOK.get(args.model, {"input": 0.0, "output": 0.0})
    embed_price = PRICE_PER_MTOK.get(args.embed_model, {"input": 0.0, "output": 0.0})
    counted = estimated if args.dry_run else usage
    cost = (
        counted["input_tokens"] / 1e6 * chat_price["input"]
        + counted["output_tokens"] / 1e6 * chat_price["output"]
        + counted["embedding_tokens"] / 1e6 * embed_price["input"]
    )

    print()
    print(f"cache hits / new calls   : {cache.hits} / {estimated['calls']}")
    print(f"few-shot predictions     : {len(results_fewshot)}")
    print(f"RAG predictions          : {len(results_rag)}")
    print(
        "tokens (%s)        : %d in, %d out, %d embedding"
        % (
            "estimated" if args.dry_run else "billed   ",
            counted["input_tokens"],
            counted["output_tokens"],
            counted["embedding_tokens"],
        )
    )
    print(f"cost {'estimate' if args.dry_run else 'actual  '}            : USD {cost:.4f}")

    if args.dry_run:
        print("\nDry run: no request was sent and nothing was written.")
        return 0

    output.mkdir(parents=True, exist_ok=True)
    if results_fewshot:
        (output / "results_fewshot.json").write_text(
            json.dumps(results_fewshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if results_rag:
        (output / "results_rag.json").write_text(
            json.dumps(results_rag, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    manifest = {
        "experiment_id": output.name,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Regenerate the historical few-shot and RAG baselines over the frozen "
            "question wording so the three-system comparison covers all 98 records."
        ),
        "inputs": {
            "benchmark": str(args.benchmark),
            "benchmark_sha256": sha256_file(args.benchmark.resolve()),
            "qa_pairs_sha256": sha256_file(args.qa_pairs.resolve()),
            "chunks_sha256": sha256_file(args.chunks.resolve()),
            "records": len(records),
            "chunks_indexed": len(chunks),
        },
        "parameters": {
            "model": args.model,
            "embed_model": args.embed_model,
            "temperature": TEMPERATURE,
            "k_shots": list(K_SHOTS),
            "rag_top_k": list(TOP_K_VALUES),
            "random_seed": RANDOM_SEED,
            "retrieval": "numpy cosine over L2-normalised vectors (faiss IndexFlatIP equivalent)",
        },
        "usage": {
            "new_api_calls": usage["calls"],
            "cache_hits": cache.hits,
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "embedding_tokens": usage["embedding_tokens"],
            "estimated_cost_usd": round(cost, 4),
        },
        "outputs": {
            name: sha256_file(output / name)
            for name in ("results_fewshot.json", "results_rag.json")
            if (output / name).exists()
        },
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nWritten to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
