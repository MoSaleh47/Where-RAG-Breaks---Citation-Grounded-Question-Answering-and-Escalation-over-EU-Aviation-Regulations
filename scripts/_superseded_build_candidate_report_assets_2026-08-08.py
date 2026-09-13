"""Build candidate-only retrieval figures from saved experiment metrics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


SYSTEMS = (
    ("BM25", "bm25"),
    ("Dense / 3-small", "dense_small"),
    ("Dense / 3-large", "dense_large"),
    ("Hybrid RRF", "hybrid"),
    ("Hybrid + reranker", "reranker"),
)
K_VALUES = (1, 3, 5, 10, 20)
COLORS = {
    "BM25": "#6B7280",
    "Dense / 3-small": "#9CA3AF",
    "Dense / 3-large": "#4B5563",
    "Hybrid RRF": "#2563EB",
    "Hybrid + reranker": "#D97706",
}
MARKERS = {
    "BM25": "o",
    "Dense / 3-small": "s",
    "Dense / 3-large": "^",
    "Hybrid RRF": "D",
    "Hybrid + reranker": "P",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_test_metrics(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    test = payload["test"]
    missing = sorted(set(map(str, K_VALUES)) - set(test))
    if missing:
        raise ValueError(f"{path} is missing test cutoffs {missing}")
    return test


def main() -> int:
    parser = argparse.ArgumentParser()
    for _, key in SYSTEMS:
        parser.add_argument(f"--{key.replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    paths = {
        key: getattr(args, key).resolve()
        for _, key in SYSTEMS
    }
    metrics = {
        label: load_test_metrics(paths[key])
        for label, key in SYSTEMS
    }
    sample_sizes = {
        values[str(k)]["n"]
        for values in metrics.values()
        for k in K_VALUES
    }
    if len(sample_sizes) != 1:
        raise SystemExit(f"Experiments use inconsistent test sample sizes: {sample_sizes}")
    sample_size = sample_sizes.pop()

    rows = []
    for label, _ in SYSTEMS:
        for k in K_VALUES:
            row = {
                "system": label,
                "split": "test",
                "k": k,
                **metrics[label][str(k)],
            }
            rows.append(row)
    csv_path = output / "candidate_retrieval_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#1F2937",
            "text.color": "#111827",
            "xtick.color": "#374151",
            "ytick.color": "#374151",
        }
    )
    figure, (curve_ax, bar_ax) = plt.subplots(
        1,
        2,
        figsize=(13.5, 6.2),
        gridspec_kw={"width_ratios": [1.45, 1]},
    )
    figure.patch.set_facecolor("white")

    for label, _ in SYSTEMS:
        values = [
            100 * metrics[label][str(k)]["any_gold_child_recall"]
            for k in K_VALUES
        ]
        curve_ax.plot(
            K_VALUES,
            values,
            color=COLORS[label],
            marker=MARKERS[label],
            linewidth=2.2 if "Hybrid" in label else 1.5,
            markersize=7,
            label=label,
        )
    curve_ax.set_title("A. Candidate retrieval recall by cutoff", loc="left")
    curve_ax.set_xlabel("Retrieved children (k)")
    curve_ax.set_ylabel("Questions with at least 1 candidate-gold child (%)")
    curve_ax.set_xticks(K_VALUES)
    curve_ax.set_ylim(35, 100)
    curve_ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    curve_ax.legend(frameon=False, loc="lower right", fontsize=9)

    operating_k = (5, 10, 20)
    positions = list(range(len(operating_k)))
    width = 0.34
    for offset, label in ((-width / 2, "Hybrid RRF"), (width / 2, "Hybrid + reranker")):
        values = [
            100 * metrics[label][str(k)]["any_gold_child_recall"]
            for k in operating_k
        ]
        bars = bar_ax.bar(
            [position + offset for position in positions],
            values,
            width=width,
            color=COLORS[label],
            label=label,
        )
        bar_ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
    bar_ax.set_title("B. Reranking improves order, not the pool ceiling", loc="left")
    bar_ax.set_xlabel("Retrieved children (k)")
    bar_ax.set_ylabel("Candidate exact-child recall (%)")
    bar_ax.set_xticks(positions, [str(k) for k in operating_k])
    bar_ax.set_ylim(65, 100)
    bar_ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    bar_ax.legend(frameon=False, loc="lower right", fontsize=9)
    bar_ax.annotate(
        "Same ceiling: 54/57",
        xy=(2.17, 94.7368),
        xytext=(1.35, 91.0),
        arrowprops={"arrowstyle": "->", "color": "#374151"},
        fontsize=9,
        color="#374151",
    )

    figure.suptitle(
        "Held-out retrieval results before independent benchmark review",
        x=0.06,
        y=0.98,
        ha="left",
        fontsize=16,
        fontweight="bold",
    )
    figure.text(
        0.06,
        0.93,
        (
            f"Candidate benchmark | test n={sample_size} | parent-grouped split | "
            "percentages must be regenerated after review"
        ),
        ha="left",
        fontsize=10,
        color="#4B5563",
    )
    figure.text(
        0.5,
        0.5,
        "CANDIDATE - INDEPENDENT REVIEW PENDING",
        ha="center",
        va="center",
        rotation=20,
        fontsize=27,
        color="#B91C1C",
        alpha=0.075,
        fontweight="bold",
    )
    figure.text(
        0.06,
        0.025,
        (
            "Metric: any-gold-child recall on the current AI-assisted candidate labels. "
            "Source: saved experiment retrieval_metrics.json files."
        ),
        ha="left",
        fontsize=8.5,
        color="#6B7280",
    )
    figure.tight_layout(rect=(0.04, 0.07, 0.99, 0.9), w_pad=3.2)

    png_path = output / "candidate_retrieval_comparison.png"
    svg_path = output / "candidate_retrieval_comparison.svg"
    figure.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
    figure.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.close(figure)

    manifest = {
        "asset_id": "candidate_retrieval_comparison_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "candidate_independent_review_pending",
        "test_question_count": sample_size,
        "metric": "any_gold_child_recall",
        "cutoffs": list(K_VALUES),
        "inputs": {
            key: {
                "path": str(path),
                "sha256": sha256(path),
            }
            for key, path in paths.items()
        },
        "outputs": {
            "csv_sha256": sha256(csv_path),
            "png_sha256": sha256(png_path),
            "svg_sha256": sha256(svg_path),
        },
        "software": {
            "python": sys.version,
            "matplotlib": matplotlib.__version__,
            "platform": platform.platform(),
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

