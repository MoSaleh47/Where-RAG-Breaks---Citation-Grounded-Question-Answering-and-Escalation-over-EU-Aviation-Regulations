"""Evaluate escalation rules against runtime-observable signals (development only).

A signal qualifies only if it can be computed at the moment a user asks the
question, with no gold labels. Retrieval scores, the verifier's output and the
shape of the generated answer all qualify. Whether the answer selected the right
provision does not -- that is the outcome being predicted.

The script deliberately does not choose a threshold. It emits every candidate
rule with its escalation rate, precision, recall and a Wilson interval, plus the
sample size that would be needed to distinguish each precision from the observed
base error rate. On the current development split every interval contains or
nearly contains the base rate, and D040 records the decision not to fit a
threshold to nine error events.

Refuses to run on anything but the development split unless explicitly overridden,
for the reason in D036: a policy calibrated and evaluated on the same records
measures nothing.

Usage:

    python scripts/calibrate_escalation.py \\
        --answers experiments/E5_generation_top5_dev_v2/answers.jsonl \\
        --reranked experiments/E4_cross_encoder_rerank_reviewed_v1/rankings.jsonl \\
        --hybrid experiments/E3_hybrid_rrf_reviewed_v1/rankings.jsonl \\
        --benchmark data/evaluation/reviewed_benchmark_v1/reviewed_benchmark.jsonl \\
        --output experiments/escalation_dev_v1
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_jsonl(path: Path) -> dict[str, dict]:
    return {
        json.loads(line)["qa_id"]: json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def wilson(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    if trials == 0:
        return (0.0, 1.0)
    proportion = successes / trials
    denominator = 1 + z * z / trials
    centre = proportion + z * z / (2 * trials)
    spread = z * math.sqrt(
        proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)
    )
    return ((centre - spread) / denominator, (centre + spread) / denominator)


def required_sample(base: float, target: float) -> int | None:
    """Two-proportion sample size, alpha 0.05, power 0.80, per group."""
    if target <= base:
        return None
    pooled = (base + target) / 2
    numerator = (
        1.96 * math.sqrt(2 * pooled * (1 - pooled))
        + 0.84 * math.sqrt(base * (1 - base) + target * (1 - target))
    ) ** 2
    return math.ceil(numerator / ((target - base) ** 2))


def build_signals(answers, reranked, hybrid, benchmark) -> list[dict]:
    rows = []
    for qa_id, answer in answers.items():
        rerank = reranked[qa_id]["ranking"]
        fused = hybrid[qa_id]["ranking"]
        record = benchmark[qa_id]
        payload = answer["answer"] or {}
        cited = {
            support["source_id"]
            for claim in payload.get("claims", [])
            for support in claim.get("supports", [])
        }
        child_to_parent = {item["child_id"]: item["parent_id"] for item in rerank}
        verification = answer["verification"]
        rows.append(
            {
                "qa_id": qa_id,
                "split": answer["split"],
                # --- runtime signals, no gold labels ---
                "rerank_top1_score": round(rerank[0]["score"], 6),
                "rerank_margin": round(rerank[0]["score"] - rerank[1]["score"], 6),
                "rerank_top5_mean": round(
                    statistics.mean(item["score"] for item in rerank[:5]), 6
                ),
                "top1_rank_shift": abs(rerank[0]["hybrid_original_rank"] - 1),
                "hybrid_margin": round(fused[0]["score"] - fused[1]["score"], 8),
                "distinct_parents_top5": len(
                    {item["parent_id"] for item in rerank[:5]}
                ),
                "claim_count": len(payload.get("claims", [])),
                "distinct_sources_cited": len(cited),
                "answer_words": len(payload.get("answer_text", "").split()),
                "quote_pass": int(verification["quote_pass"]),
                "quote_pass_strict": int(verification.get("quote_pass_strict", False)),
                "elided_quote": int(bool(verification.get("elided_quotes"))),
                "model_abstained": int(bool(payload.get("abstain"))),
                # --- outcome, gold labels, development only ---
                "evidence_correct": int(bool(cited & set(record["gold_child_ids"]))),
                "parent_correct": int(
                    bool(
                        {child_to_parent.get(source) for source in cited}
                        & set(record["acceptable_parent_ids"])
                    )
                ),
            }
        )
    return rows


RULES = [
    ("reranker moved top-1 by >= 2 ranks", lambda r: r["top1_rank_shift"] >= 2),
    ("reranker moved top-1 by >= 3 ranks", lambda r: r["top1_rank_shift"] >= 3),
    ("reranker moved top-1 by >= 5 ranks", lambda r: r["top1_rank_shift"] >= 5),
    ("rerank margin <= 0.5", lambda r: r["rerank_margin"] <= 0.5),
    ("rerank margin <= 1.0", lambda r: r["rerank_margin"] <= 1.0),
    ("rerank margin <= 1.5", lambda r: r["rerank_margin"] <= 1.5),
    ("cited <= 1 distinct source", lambda r: r["distinct_sources_cited"] <= 1),
    ("cited <= 2 distinct sources", lambda r: r["distinct_sources_cited"] <= 2),
    ("only one claim made", lambda r: r["claim_count"] <= 1),
    ("quote verification failed", lambda r: not r["quote_pass"]),
    ("byte-strict quote check failed", lambda r: not r["quote_pass_strict"]),
    ("model abstained", lambda r: bool(r["model_abstained"])),
    (
        "moved >= 2 ranks OR quote failed",
        lambda r: r["top1_rank_shift"] >= 2 or not r["quote_pass"],
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", required=True, type=Path)
    parser.add_argument("--reranked", required=True, type=Path)
    parser.add_argument("--hybrid", required=True, type=Path)
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--split", default="development")
    parser.add_argument(
        "--allow-non-development",
        action="store_true",
        help="Calibrating on anything but development contaminates the held-out split.",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.split != "development" and not args.allow_non_development:
        raise SystemExit(
            f"Refusing to calibrate on '{args.split}'. Selection happens on "
            "development data only."
        )

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    paths = {
        "answers": args.answers.resolve(),
        "reranked": args.reranked.resolve(),
        "hybrid": args.hybrid.resolve(),
        "benchmark": args.benchmark.resolve(),
    }
    rows = build_signals(
        read_jsonl(paths["answers"]),
        read_jsonl(paths["reranked"]),
        read_jsonl(paths["hybrid"]),
        read_jsonl(paths["benchmark"]),
    )
    rows = [row for row in rows if row["split"] == args.split]
    if not rows:
        raise SystemExit(f"No records on split '{args.split}'")

    total = len(rows)
    errors = [row for row in rows if not row["evidence_correct"]]
    base_rate = len(errors) / total

    evaluated = []
    for name, predicate in RULES:
        escalated = [row for row in rows if predicate(row)]
        caught = [row for row in escalated if not row["evidence_correct"]]
        precision = len(caught) / len(escalated) if escalated else None
        low, high = wilson(len(caught), len(escalated))
        evaluated.append(
            {
                "rule": name,
                "escalated": len(escalated),
                "escalation_rate": round(len(escalated) / total, 4),
                "errors_caught": len(caught),
                "precision": round(precision, 4) if precision is not None else None,
                "precision_ci95": [round(low, 4), round(high, 4)] if escalated else None,
                "recall": round(len(caught) / len(errors), 4) if errors else None,
                "beats_base_rate_at_95": bool(escalated) and low > base_rate,
            }
        )

    quote_failures = [row for row in rows if not row["quote_pass"]]
    overlap = [
        row for row in rows if not row["quote_pass"] and not row["evidence_correct"]
    ]

    summary = {
        "status": "development_only_uncalibrated",
        "split": args.split,
        "record_count": total,
        "base_error_rate": round(base_rate, 4),
        "error_events": len(errors),
        "failure_mode_overlap": {
            "wrong_evidence_selected": len(errors),
            "quote_not_grounded": len(quote_failures),
            "both": len(overlap),
            "either": len(
                {row["qa_id"] for row in errors} | {row["qa_id"] for row in quote_failures}
            ),
            "note": (
                "Zero overlap means quote verification carries no information about "
                "evidence selection, and vice versa. Both layers are required."
            ),
        },
        "rules": evaluated,
        "any_rule_beats_base_rate_at_95": any(
            rule["beats_base_rate_at_95"] for rule in evaluated
        ),
        "required_sample_sizes": {
            f"precision_{target:.2f}": {
                "escalated_decisions": required_sample(base_rate, target),
                "questions_at_observed_escalation_rate": (
                    math.ceil(required_sample(base_rate, target) / 0.45)
                    if required_sample(base_rate, target)
                    else None
                ),
            }
            for target in (0.35, 0.42, 0.50, 0.60)
        },
        "conclusion": (
            "No escalation threshold is fitted. With this many error events every "
            "candidate rule's precision interval contains or nearly contains the base "
            "error rate, so any threshold chosen here would be indistinguishable from "
            "noise. The policy is specified and its retrieval-uncertainty thresholds "
            "are left open; see D040. Quote-verification gating needs no calibration "
            "and is applied unconditionally; see D042."
        ),
    }

    signals_path = output / "signals.csv"
    with signals_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    calibration_path = output / "calibration.json"
    calibration_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "experiment_id": output.name,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "development_only_uncalibrated",
        "model_calls": 0,
        "inputs": {f"{name}_sha256": sha256(path) for name, path in paths.items()},
        "outputs": {
            "signals_sha256": sha256(signals_path),
            "calibration_sha256": sha256(calibration_path),
        },
        "software": {"python": sys.version, "platform": platform.platform()},
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(f"n={total}  base error rate={base_rate:.3f}  error events={len(errors)}")
    header = f"{'rule':<38}{'esc':>5}{'prec':>7}{'ci95':>16}{'recall':>8}"
    print("\n" + header)
    print("-" * len(header))
    for rule in evaluated:
        ci = (
            f"[{rule['precision_ci95'][0]:.2f},{rule['precision_ci95'][1]:.2f}]"
            if rule["precision_ci95"]
            else "-"
        )
        precision = f"{rule['precision']:.2f}" if rule["precision"] is not None else "-"
        recall = f"{rule['recall']:.2f}" if rule["recall"] is not None else "-"
        print(f"{rule['rule']:<38}{rule['escalated']:>5}{precision:>7}{ci:>16}{recall:>8}")
    print(
        f"\nany rule beating the base rate at 95%: "
        f"{summary['any_rule_beats_base_rate_at_95']}"
    )
    print(f"failure-mode overlap: {summary['failure_mode_overlap']['both']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
