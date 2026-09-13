"""Re-run the full retrieval stack against the frozen reviewed benchmark.

Every stage is an existing entry point; this driver only fixes the paths so the
reviewed run cannot be confused with the candidate run and cannot overwrite it.

    python scripts/rerun_reviewed_retrieval.py

Completed stages are skipped automatically, so a failure part-way through costs
only the stages that had not finished. Nothing is recomputed unless you ask:

    --force              re-run every stage, overwriting reviewed outputs
    --only 2 3           run only these stage numbers
    --python <path>      use a different interpreter (see below)
    --list               show what would run, then exit

Dependencies. Stages 2 and 3 need `openai` and `python-dotenv`; stage 4 needs
`torch` and `transformers`; stage 5 needs `matplotlib`. The driver checks these
before running anything and prints the exact pip command if something is
missing. The candidate runs were made on Python 3.10.11 with openai 2.24.0 --
if that interpreter is still on this machine and already has the packages,
point at it with --python instead of installing into the current environment:

    python scripts/rerun_reviewed_retrieval.py --python C:\\Path\\To\\python.exe

What each stage costs. Stages 1, 4 and 5 are local and free. Stages 2 and 3 send
the 98 reviewed questions to the OpenAI embeddings API -- roughly 2,500 tokens
per model, authorised under D013. The 1,535 corpus vectors are copied from the
candidate cache and are never re-sent. Stage 4 downloads the MiniLM cross-encoder
from Hugging Face on first use if it is not already in the local cache; no
project text leaves the machine.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BENCH = ROOT / "data/evaluation/reviewed_benchmark_v1/reviewed_benchmark.jsonl"
SPLIT = ROOT / "data/evaluation/reviewed_benchmark_v1/split_manifest.csv"
CHILDREN = ROOT / "data/processed/E1_parent_child_v1/children.jsonl"

CANDIDATE_CACHE = ROOT / "experiments/cache/embeddings/E1_parent_child_v1"
REVIEWED_CACHE = ROOT / "experiments/cache/embeddings/reviewed_benchmark_v1"
# NOTE: --score-cache is a FILE, not a directory. A new name keeps the candidate
# reranker cache intact.
RERANK_SCORES = (
    ROOT / "experiments/cache/rerankers/ms-marco-MiniLM-L6-v2"
    / "reviewed_hybrid_top20_scores.json"
)

EXP = ROOT / "experiments"
BM25_DIR = EXP / "BM25_local_reviewed_v1"
SMALL_DIR = EXP / "E1_dense_3small_reviewed_v1"
LARGE_DIR = EXP / "E2_dense_3large_reviewed_v1"
HYBRID_DIR = EXP / "E3_hybrid_rrf_reviewed_v1"
RERANK_DIR = EXP / "E4_cross_encoder_rerank_reviewed_v1"
ASSETS_DIR = ROOT / "reports/assets/reviewed_v1"


def stages() -> list[dict]:
    """Stage definitions. `needs` are importable module names, not pip names."""
    return [
        {
            "n": 1,
            "label": "BM25 (local)",
            "out": BM25_DIR,
            "needs": [],
            "argv": [
                "scripts/run_bm25_retrieval.py",
                "--children", str(CHILDREN),
                "--audited-qa", str(BENCH),
                "--split-manifest", str(SPLIT),
                "--output", str(BM25_DIR),
            ],
        },
        {
            "n": 2,
            "label": "Dense / text-embedding-3-small (embeds 98 questions)",
            "out": SMALL_DIR,
            "needs": ["openai", "dotenv", "numpy"],
            "argv": [
                "scripts/run_dense_retrieval.py",
                "--children", str(CHILDREN),
                "--audited-qa", str(BENCH),
                "--split-manifest", str(SPLIT),
                "--output", str(SMALL_DIR),
                "--cache", str(REVIEWED_CACHE),
                "--model", "text-embedding-3-small",
            ],
        },
        {
            "n": 3,
            "label": "Dense / text-embedding-3-large (embeds 98 questions)",
            "out": LARGE_DIR,
            "needs": ["openai", "dotenv", "numpy"],
            "argv": [
                "scripts/run_dense_retrieval.py",
                "--children", str(CHILDREN),
                "--audited-qa", str(BENCH),
                "--split-manifest", str(SPLIT),
                "--output", str(LARGE_DIR),
                "--cache", str(REVIEWED_CACHE),
                "--model", "text-embedding-3-large",
            ],
        },
        {
            "n": 4,
            "label": "Hybrid RRF, equal weights, c=60 (local)",
            "out": HYBRID_DIR,
            "needs": [],
            "requires_outputs": [
                LARGE_DIR / "rankings.jsonl",
                BM25_DIR / "rankings.jsonl",
            ],
            "argv": [
                "scripts/run_rrf_fusion.py",
                "--dense-rankings", str(LARGE_DIR / "rankings.jsonl"),
                "--lexical-rankings", str(BM25_DIR / "rankings.jsonl"),
                "--output", str(HYBRID_DIR),
            ],
        },
        {
            "n": 5,
            "label": "Cross-encoder reranking (local model)",
            "out": RERANK_DIR,
            "needs": ["torch", "transformers"],
            "requires_outputs": [HYBRID_DIR / "rankings.jsonl"],
            "argv": [
                "scripts/run_cross_encoder_reranking.py",
                "--hybrid-rankings", str(HYBRID_DIR / "rankings.jsonl"),
                "--children", str(CHILDREN),
                "--audited-qa", str(BENCH),
                "--output", str(RERANK_DIR),
                "--score-cache", str(RERANK_SCORES),
            ],
        },
        {
            "n": 6,
            "label": "Figures and CSV data",
            "out": ASSETS_DIR,
            "needs": ["matplotlib"],
            "requires_outputs": [
                BM25_DIR / "retrieval_metrics.json",
                SMALL_DIR / "retrieval_metrics.json",
                LARGE_DIR / "retrieval_metrics.json",
                HYBRID_DIR / "retrieval_metrics.json",
                RERANK_DIR / "retrieval_metrics.json",
            ],
            "argv": [
                "scripts/build_candidate_report_assets.py",
                "--bm25", str(BM25_DIR / "retrieval_metrics.json"),
                "--dense-small", str(SMALL_DIR / "retrieval_metrics.json"),
                "--dense-large", str(LARGE_DIR / "retrieval_metrics.json"),
                "--hybrid", str(HYBRID_DIR / "retrieval_metrics.json"),
                "--reranker", str(RERANK_DIR / "retrieval_metrics.json"),
                "--output", str(ASSETS_DIR),
            ],
        },
    ]


PIP_NAME = {
    "dotenv": "python-dotenv",
    "openai": "openai",
    "numpy": "numpy",
    "torch": "torch",
    "transformers": "transformers",
    "matplotlib": "matplotlib",
}


def is_complete(stage: dict) -> bool:
    out = stage["out"]
    return out.exists() and any(out.iterdir())


def missing_modules(python: str, modules: list[str]) -> list[str]:
    if not modules:
        return []
    probe = (
        "import importlib.util as u, sys; "
        f"print(','.join(m for m in {modules!r} if u.find_spec(m) is None))"
    )
    result = subprocess.run(
        [python, "-c", probe], capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Could not probe the interpreter {python}:\n{result.stderr.strip()}"
        )
    return [m for m in result.stdout.strip().split(",") if m]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only", nargs="+", type=int, metavar="N")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    for path in (BENCH, SPLIT, CHILDREN):
        if not path.exists():
            raise SystemExit(f"Missing input: {path}\nFreeze the benchmark first.")

    all_stages = stages()
    selected = [s for s in all_stages if not args.only or s["n"] in args.only]
    if not selected:
        raise SystemExit(f"--only matched no stage; valid numbers are 1-{len(all_stages)}")

    todo, skipped = [], []
    for stage in selected:
        (skipped if is_complete(stage) and not args.force else todo).append(stage)

    print(f"interpreter: {args.python}")
    for stage in skipped:
        print(f"  skip  {stage['n']}. {stage['label']}  (output already exists)")
    for stage in todo:
        print(f"  run   {stage['n']}. {stage['label']}")
    if not todo:
        print("\nNothing to do. Use --force to re-run, or --only N for one stage.")
        return 0
    if args.list:
        return 0

    # Check every dependency up front so a long stage never fails at the end
    # because a later one cannot import.
    needed = sorted({m for stage in todo for m in stage["needs"]})
    absent = missing_modules(args.python, needed)
    if absent:
        packages = " ".join(sorted({PIP_NAME.get(m, m) for m in absent}))
        blocked = [s["n"] for s in todo if set(s["needs"]) & set(absent)]
        print(f"\nMissing modules for stage(s) {blocked}: {', '.join(absent)}")
        print("\nEither install them into this environment:")
        print(f"    python -m pip install {packages}")
        print("\nor point the driver at the interpreter the candidate runs used")
        print("(Python 3.10.11, which already has openai 2.24.0):")
        print("    python scripts/rerun_reviewed_retrieval.py --python <path-to-python.exe>")
        print("\nStages that do not need them can still be run now, for example:")
        runnable = [s["n"] for s in todo if not set(s["needs"]) & set(absent)]
        if runnable:
            print(f"    python scripts/rerun_reviewed_retrieval.py --only "
                  f"{' '.join(str(n) for n in runnable)}")
        return 1

    # Reuse the corpus vectors so only the questions are re-embedded.
    if any(stage["n"] in (2, 3) for stage in todo):
        REVIEWED_CACHE.mkdir(parents=True, exist_ok=True)
        for pattern in ("*_children.npy", "*_children.json"):
            for source in CANDIDATE_CACHE.glob(pattern):
                target = REVIEWED_CACHE / source.name
                if not target.exists():
                    shutil.copyfile(source, target)
                    print(f"corpus vectors reused: {target.name}")

    for stage in todo:
        for required in stage.get("requires_outputs", []):
            if not required.exists():
                raise SystemExit(
                    f"Stage {stage['n']} needs {required.relative_to(ROOT)}, which does "
                    f"not exist. Run the earlier stages first."
                )
        print(f"\n{'=' * 70}\n{stage['n']}/{len(all_stages)}  {stage['label']}\n{'=' * 70}",
              flush=True)
        argv = list(stage["argv"]) + (["--force"] if args.force else [])
        result = subprocess.run([args.python, *argv], cwd=ROOT)
        if result.returncode != 0:
            print(
                f"\nFAILED at stage {stage['n']}: {stage['label']} (exit {result.returncode})"
                f"\nCompleted stages are kept. Fix the cause and re-run the same command -- "
                f"finished stages are skipped automatically."
            )
            return result.returncode

    print("\nDone. Reviewed-label metrics are in:")
    for path in (BM25_DIR, SMALL_DIR, LARGE_DIR, HYBRID_DIR, RERANK_DIR, ASSETS_DIR):
        print(f"  {path.relative_to(ROOT)}")
    print(
        "\nThe candidate runs and their caches are untouched, so the pre-review "
        "figures remain reproducible for the before/after comparison in Chapter 5."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
