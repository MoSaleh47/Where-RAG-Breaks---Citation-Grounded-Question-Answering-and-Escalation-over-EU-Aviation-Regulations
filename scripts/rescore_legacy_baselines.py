"""Re-score the stored few-shot / RAG / LoRA predictions on the frozen benchmark.

No model is called. The predictions in ``Documents/results_*.json`` are read as
they were produced; only the labels they are scored against and the scorer
itself change.

Three citation measures are reported side by side, because the point of the
exercise is to show what the original measure was counting.

``legacy``
    The original scorer, reproduced exactly: substring containment of the gold
    citation, with half credit for naming the article number, thresholded at
    0.5 together with ROUGE-L >= 0.15. Reported for continuity only. It is not
    a correctness measure and must never be described as accuracy.

``parent``
    The prediction names a citation that resolves, against the parent corpus, to
    the provision the gold citation denotes. Verifiable against a stored
    artifact rather than against a string.

``exact``
    Every atomic unit of the gold citation, down to the sub-paragraph, is named
    in the prediction.

Scope. Two records were excluded by the review, and eight questions were
reworded, which makes the stored predictions answers to a different question.
Those ten are dropped from the primary comparison and listed in the output, so
the comparison is over the records where a stored prediction is still a valid
answer.

Usage:

    python scripts/rescore_legacy_baselines.py \\
        --benchmark data/evaluation/reviewed_benchmark_v1/reviewed_benchmark.jsonl \\
        --parents data/processed/E1_parent_child_v1/parents.jsonl \\
        --split-manifest data/evaluation/reviewed_benchmark_v1/split_manifest.csv \\
        --chunk-parent-map data/evaluation/legacy_to_e1_v1/legacy_chunk_parent_map.csv \\
        --results ../Documents/results_fewshot.json ../Documents/results_rag.json \\
                  ../Documents/results_lora.json \\
        --output experiments/legacy_baselines_reviewed_v1
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.evaluation.citations import (  # noqa: E402
    ParentResolver,
    exact_citation_match,
    legacy_citation_match,
    parent_citation_match,
    parse_citations,
)

ROUGE_FLOOR = 0.15
LEGACY_CITATION_FLOOR = 0.5


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


# --- ROUGE-L, reproduced verbatim from the original evaluator ---------------
# Kept identical so that a change in the reported number can only come from the
# labels or the sample, never from the content measure.


def _lcs_length(a: str, b: str) -> int:
    a_tokens, b_tokens = a.lower().split(), b.lower().split()
    m, n = len(a_tokens), len(b_tokens)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = (
                dp[i - 1][j - 1] + 1
                if a_tokens[i - 1] == b_tokens[j - 1]
                else max(dp[i - 1][j], dp[i][j - 1])
            )
    return dp[m][n]


def rouge_l(prediction: str, reference: str) -> float:
    if not prediction or not reference:
        return 0.0
    predicted_length = len(prediction.lower().split())
    reference_length = len(reference.lower().split())
    if predicted_length == 0 or reference_length == 0:
        return 0.0
    lcs = _lcs_length(prediction, reference)
    precision = lcs / predicted_length
    recall = lcs / reference_length
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


def has_citation(text: str) -> int:
    return 1 if re.search(r"\[.+?\]", text) else 0


def normalise_question(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def variant_of(record: dict) -> str:
    return str(record.get("variant", record.get("k_shots", record.get("k", "?"))))


def system_of(record: dict, source: Path) -> str:
    declared = record.get("system")
    if declared:
        return str(declared)
    stem = source.stem.lower()
    for name in ("fewshot", "rag", "lora"):
        if name in stem:
            return name
    return stem


def retrieved_parents(record: dict, chunk_parent: dict[str, str]) -> set[str]:
    raw = record.get("retrieved_chunks")
    if not raw:
        return set()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return set()
    parents = set()
    for item in raw:
        chunk_id = item.get("chunk_id") if isinstance(item, dict) else item
        parent = chunk_parent.get(str(chunk_id))
        if parent:
            parents.add(parent)
    return parents


def mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--parents", required=True, type=Path)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--chunk-parent-map", type=Path)
    parser.add_argument("--results", required=True, nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    benchmark_path = args.benchmark.resolve()
    parents_path = args.parents.resolve()
    split_path = args.split_manifest.resolve()

    benchmark = {record["qa_id"]: record for record in read_jsonl(benchmark_path)}
    resolver = ParentResolver.from_parents(read_jsonl(parents_path))
    split_by_qa = {row["qa_id"]: row["split"] for row in read_csv(split_path)}

    chunk_parent: dict[str, str] = {}
    if args.chunk_parent_map:
        for row in read_csv(args.chunk_parent_map.resolve()):
            if row.get("parent_id"):
                chunk_parent[row["legacy_chunk_id"]] = row["parent_id"]

    rows: list[dict] = []
    excluded_by_review: set[str] = set()
    reworded: set[str] = set()

    for source in args.results:
        source = source.resolve()
        for record in json.loads(source.read_text(encoding="utf-8")):
            qa_id = record.get("qa_id", "")
            gold = benchmark.get(qa_id)
            if gold is None:
                excluded_by_review.add(qa_id)
                continue
            if normalise_question(record.get("question")) != normalise_question(
                gold["question"]
            ):
                reworded.add(qa_id)
                continue

            prediction = record.get("prediction", "") or ""
            gold_citation = gold["acceptable_citation"]
            gold_answer = gold["reference_answer"]

            legacy_score = legacy_citation_match(prediction, gold_citation)
            content = rouge_l(prediction, gold_answer)
            exact, missing_units = exact_citation_match(prediction, gold_citation)
            parent_ok, detail = parent_citation_match(prediction, gold_citation, resolver)

            predicted_units = parse_citations(prediction)
            retrieval_hit = None
            if record.get("retrieved_chunks") is not None:
                hits = retrieved_parents(record, chunk_parent)
                retrieval_hit = int(bool(hits & set(gold["acceptable_parent_ids"])))

            rows.append(
                {
                    "system": system_of(record, source),
                    "variant": variant_of(record),
                    "qa_id": qa_id,
                    "split": split_by_qa.get(qa_id, ""),
                    "question_type": gold.get("question_type", ""),
                    "difficulty": gold.get("difficulty", ""),
                    "gold_citation": gold_citation,
                    "gold_parent_id": gold["parent_id"],
                    "rouge_l": content,
                    "content_above_floor": int(content >= ROUGE_FLOOR),
                    "has_citation": has_citation(prediction),
                    "legacy_citation_match": legacy_score,
                    "legacy_correct": int(
                        legacy_score >= LEGACY_CITATION_FLOOR and content >= ROUGE_FLOOR
                    ),
                    "parent_citation_correct": "" if parent_ok is None else int(parent_ok),
                    "exact_citation_correct": "" if exact is None else int(exact),
                    "gold_citation_ambiguous": int(detail["gold_ambiguous"]),
                    "gold_citation_resolvable": int(parent_ok is not None),
                    "predicted_citations": "; ".join(str(unit) for unit in predicted_units),
                    "missing_exact_units": "; ".join(missing_units),
                    "retrieval_parent_hit": "" if retrieval_hit is None else retrieval_hit,
                }
            )

    if not rows:
        raise SystemExit("No comparable records were scored; check the input paths.")

    per_record = output / "per_record.csv"
    with per_record.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def aggregate(subset: list[dict]) -> dict:
        parent_defined = [r for r in subset if r["parent_citation_correct"] != ""]
        exact_defined = [r for r in subset if r["exact_citation_correct"] != ""]
        retrieval_defined = [r for r in subset if r["retrieval_parent_hit"] != ""]
        return {
            "n": len(subset),
            "rouge_l": mean([r["rouge_l"] for r in subset]),
            "has_citation": mean([r["has_citation"] for r in subset]),
            "legacy_loose_correct": mean([r["legacy_correct"] for r in subset]),
            "parent_citation_correct": mean(
                [r["parent_citation_correct"] for r in parent_defined]
            ),
            "parent_citation_n": len(parent_defined),
            "exact_citation_correct": mean(
                [r["exact_citation_correct"] for r in exact_defined]
            ),
            "exact_citation_n": len(exact_defined),
            "grounded_and_supported": mean(
                [
                    int(r["parent_citation_correct"] == 1 and r["content_above_floor"] == 1)
                    for r in parent_defined
                ]
            ),
            "retrieval_parent_hit": mean(
                [r["retrieval_parent_hit"] for r in retrieval_defined]
            ),
            "unresolvable_gold_citations": sum(
                1 for r in subset if r["gold_citation_resolvable"] == 0
            ),
            "ambiguous_gold_citations": sum(
                1 for r in subset if r["gold_citation_ambiguous"] == 1
            ),
        }

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["system"], row["variant"])].append(row)

    results: dict[str, dict] = {}
    for (system, variant), subset in sorted(grouped.items()):
        results[f"{system}/{variant}"] = {
            "all": aggregate(subset),
            "development": aggregate([r for r in subset if r["split"] == "development"]),
            "test": aggregate([r for r in subset if r["split"] == "test"]),
        }

    scored_ids = sorted({row["qa_id"] for row in rows})
    summary = {
        "status": "rescored_on_frozen_reviewed_benchmark",
        "scored_record_count": len(scored_ids),
        "benchmark_record_count": len(benchmark),
        "excluded_by_review": sorted(excluded_by_review),
        "excluded_reworded_question": sorted(reworded),
        "exclusion_note": (
            "Records excluded by the independent review are absent from the frozen "
            "benchmark. Records whose question was reworded during review are "
            "dropped because the stored prediction answers the earlier wording; "
            "re-scoring them would compare an answer against a question that was "
            "never asked of the model."
        ),
        "citation_measures": {
            "legacy_loose_correct": (
                "Original scorer reproduced verbatim: substring containment with half "
                "credit for the article number, thresholded at 0.5 with ROUGE-L >= 0.15. "
                "Reported for continuity. Not a correctness measure."
            ),
            "parent_citation_correct": (
                "Prediction names a citation resolving, against the parent corpus, to "
                "the provision the gold citation denotes. Undefined where the gold "
                "citation resolves to no provision."
            ),
            "exact_citation_correct": (
                "Every atomic unit of the gold citation, including the sub-paragraph, "
                "is named in the prediction. Undefined where the gold citation cannot "
                "be parsed."
            ),
            "grounded_and_supported": (
                "parent_citation_correct AND ROUGE-L >= 0.15. The content side remains "
                "a lexical proxy and is not evidence of semantic support."
            ),
        },
        "results": results,
    }
    summary_path = output / "baseline_metrics.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    manifest = {
        "experiment_id": "legacy_baselines_reviewed_v1",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "rescored_on_frozen_reviewed_benchmark",
        "model_calls": 0,
        "inputs": {
            "benchmark_sha256": sha256(benchmark_path),
            "parents_sha256": sha256(parents_path),
            "split_manifest_sha256": sha256(split_path),
            **{
                f"{path.stem}_sha256": sha256(path.resolve()) for path in args.results
            },
        },
        "outputs": {
            "per_record_sha256": sha256(per_record),
            "baseline_metrics_sha256": sha256(summary_path),
        },
        "software": {"python": sys.version, "platform": platform.platform()},
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"scored {len(scored_ids)} records across {len(grouped)} system/variant pairs")
    print(f"excluded by review        : {sorted(excluded_by_review)}")
    print(f"excluded, question reworded: {sorted(reworded)}")
    header = f"{'system/variant':<18}{'n':>4}{'legacy':>9}{'parent':>9}{'exact':>8}{'rouge':>8}"
    print("\n" + header)
    print("-" * len(header))
    for name, payload in results.items():
        row = payload["all"]
        def show(value):
            return f"{value:.3f}" if isinstance(value, float) else "  -  "
        print(
            f"{name:<18}{row['n']:>4}{show(row['legacy_loose_correct']):>9}"
            f"{show(row['parent_citation_correct']):>9}"
            f"{show(row['exact_citation_correct']):>8}{show(row['rouge_l']):>8}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
