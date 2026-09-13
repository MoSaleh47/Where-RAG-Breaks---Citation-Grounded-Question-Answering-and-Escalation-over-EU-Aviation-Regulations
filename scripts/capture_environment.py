"""Capture the execution environment and run costs for Appendix A.

Reads the local machine for versions and hardware, then walks every experiment
manifest for the model identifiers, request counts and token counts that were
recorded at run time. Writes a JSON record and a ready-to-include LaTeX table.

Monetary cost is deliberately not guessed. Unit prices are supplied on the
command line and recorded with the date they were taken from, so the figure in
the mémoire traces to the provider's billing page rather than to an assumption
that may since have changed:

    python scripts/capture_environment.py \\
        --price-date 2026-08-12 \\
        --price gpt-4o-mini=0.15/0.60 \\
        --price text-embedding-3-small=0.02/0 \\
        --price text-embedding-3-large=0.13/0

Each --price is MODEL=INPUT/OUTPUT in US dollars per million tokens. Omit them
to report token counts with cost left explicitly uncomputed.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PACKAGES = [
    "openai", "numpy", "torch", "transformers", "sentence-transformers",
    "matplotlib", "python-dotenv", "scikit-learn", "pytest", "peft",
    "accelerate", "bitsandbytes", "safetensors",
]


def version_of(package: str) -> str | None:
    try:
        from importlib.metadata import version
        return version(package)
    except Exception:
        return None


def hardware() -> dict:
    info = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "python_version": sys.version.split()[0],
        "python_build": " ".join(platform.python_build()),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
    }
    try:
        import torch
        info["torch_cuda_available"] = torch.cuda.is_available()
        info["gpu"] = (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        )
        info["torch_version"] = torch.__version__
    except Exception:
        info["torch_cuda_available"] = None
        info["gpu"] = None
    try:
        import os
        info["cpu_count"] = os.cpu_count()
    except Exception:
        pass
    return info


def git_state() -> dict:
    def run(*args):
        try:
            return subprocess.run(
                args, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=10
            ).stdout.strip() or None
        except Exception:
            return None
    return {
        "commit": run("git", "rev-parse", "HEAD"),
        "branch": run("git", "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(run("git", "status", "--porcelain")),
    }


def walk_manifests() -> list[dict]:
    """Collect what every experiment recorded about models, calls and tokens."""
    runs = []
    for manifest_path in sorted(PROJECT_ROOT.glob("experiments/*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        summary_path = manifest_path.parent / "generation_summary.json"
        summary = {}
        if summary_path.exists():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        parameters = manifest.get("parameters", {})
        usage = summary.get("usage_tokens", {})
        models = manifest.get("parameters", {}).get("model_resolved") or []
        if isinstance(models, str):
            models = [models]
        if not models:
            single = parameters.get("model") or parameters.get("model_requested")
            models = [single] if single else []
        runs.append(
            {
                "experiment": manifest_path.parent.name,
                "experiment_id": manifest.get("experiment_id"),
                "status": manifest.get("status"),
                "completed_at_utc": manifest.get("completed_at_utc"),
                "models": models,
                "api_calls": summary.get("api_calls"),
                "cache_hits": summary.get("cache_hits"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "declared_model_calls": manifest.get("model_calls"),
                "software": manifest.get("software", {}),
            }
        )
    return runs


def embedding_tokens() -> list[dict]:
    """Embedding runs record their token count in the cache metadata.

    Caches are deduplicated on (model, texts_sha256). Vector files are copied
    between cache directories precisely so that unchanged corpus text is never
    re-embedded, and their metadata is copied with them; counting both copies
    would report tokens that were never billed. Duplicates are retained in the
    output with ``billed: false`` so the reuse is visible rather than silent.
    """
    records = []
    seen: set[tuple] = set()
    for meta in sorted(PROJECT_ROOT.glob("experiments/cache/embeddings/*/*.json")):
        try:
            payload = json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "input_tokens" not in payload:
            continue
        fingerprint = (payload.get("model"), payload.get("texts_sha256"))
        billed = fingerprint not in seen
        seen.add(fingerprint)
        records.append(
            {
                "cache": f"{meta.parent.name}/{meta.name}",
                "model": payload.get("model"),
                "count": payload.get("count"),
                "input_tokens": payload.get("input_tokens"),
                "billed": billed,
                "created_at_utc": payload.get("created_at_utc"),
            }
        )
    return records


def parse_prices(values: list[str]) -> dict:
    prices = {}
    for item in values or []:
        model, _, rates = item.partition("=")
        inp, _, out = rates.partition("/")
        try:
            prices[model.strip()] = {
                "input_per_million_usd": float(inp),
                "output_per_million_usd": float(out or 0),
            }
        except ValueError:
            raise SystemExit(f"Could not parse --price {item!r}; expected MODEL=IN/OUT")
    return prices


def cost_of(model: str, prompt: int, completion: int, prices: dict) -> float | None:
    for name, rate in prices.items():
        if model and model.startswith(name):
            return round(
                (prompt or 0) / 1e6 * rate["input_per_million_usd"]
                + (completion or 0) / 1e6 * rate["output_per_million_usd"],
                4,
            )
    return None


def latex_table(record: dict) -> str:
    hw = record["hardware"]
    rows = [
        ("Operating system", hw["platform"]),
        ("Processor", hw.get("processor") or "not reported"),
        ("Logical CPUs", str(hw.get("cpu_count") or "not reported")),
        ("GPU", hw.get("gpu") or "none used"),
        ("Python", f"{hw['python_version']} ({hw['python_implementation']})"),
    ]
    for package, version in record["packages"].items():
        if version:
            rows.append((f"\\texttt{{{package}}}", version))
    body = "\n".join(
        f"    {label} & {str(value).replace('_', chr(92) + '_')} \\\\"
        for label, value in rows
    )
    totals = record["totals"]
    cost = totals.get("estimated_cost_usd")
    cost_row = (
        f"{cost:.2f} USD" if isinstance(cost, float)
        else "not computed (unit prices not supplied)"
    )
    return f"""% Generated by scripts/capture_environment.py on {record['captured_at_utc']}.
% Do not edit by hand; re-run the script instead.
\\begin{{table}}[htbp]
  \\centering
  \\caption{{Execution environment and recorded run cost.}}
  \\label{{tab:environment}}
  \\small
  \\begin{{tabular}}{{ll}}
    \\toprule
    \\textbf{{Component}} & \\textbf{{Value}} \\\\
    \\midrule
{body}
    \\midrule
    Hosted API requests & {totals['api_calls']} \\\\
    Embedding input tokens & {totals['embedding_input_tokens_billed']:,} \\\\
    Generation prompt tokens & {totals['prompt_tokens']:,} \\\\
    Generation completion tokens & {totals['completion_tokens']:,} \\\\
    Estimated cost & {cost_row} \\\\
    \\bottomrule
  \\end{{tabular}}
\\end{{table}}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--price", action="append", metavar="MODEL=IN/OUT")
    parser.add_argument("--price-date", help="Date the unit prices were taken.")
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "docs" / "environment.json"
    )
    parser.add_argument(
        "--latex", type=Path,
        default=PROJECT_ROOT / "memoire" / "latex" / "generated" / "environment_table.tex",
    )
    args = parser.parse_args()

    prices = parse_prices(args.price)
    runs = walk_manifests()
    embeddings = embedding_tokens()

    prompt_tokens = sum(r["prompt_tokens"] or 0 for r in runs)
    completion_tokens = sum(r["completion_tokens"] or 0 for r in runs)
    api_calls = sum(r["api_calls"] or 0 for r in runs)
    embedding_input = sum(e["input_tokens"] or 0 for e in embeddings if e["billed"])
    embedding_reused = sum(e["input_tokens"] or 0 for e in embeddings if not e["billed"])

    estimated = None
    if prices:
        estimated = 0.0
        for run in runs:
            for model in run["models"]:
                value = cost_of(
                    model, run["prompt_tokens"], run["completion_tokens"], prices
                )
                if value:
                    estimated += value
        for item in embeddings:
            if not item["billed"]:
                continue
            value = cost_of(item["model"], item["input_tokens"], 0, prices)
            if value:
                estimated += value
        estimated = round(estimated, 4)

    record = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "hardware": hardware(),
        "packages": {p: version_of(p) for p in PACKAGES},
        "git": git_state(),
        "experiment_runs": runs,
        "embedding_runs": embeddings,
        "totals": {
            "api_calls": api_calls,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "embedding_input_tokens_billed": embedding_input,
            "embedding_input_tokens_reused_from_cache": embedding_reused,
            "estimated_cost_usd": estimated,
        },
        "pricing": {
            "unit_prices_usd_per_million_tokens": prices or None,
            "prices_dated": args.price_date,
            "note": (
                "Unit prices are supplied by the author from the provider's "
                "published rates on the stated date. The authoritative figure is "
                "the provider's billing record, not this estimate."
            ),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    args.latex.parent.mkdir(parents=True, exist_ok=True)
    args.latex.write_text(latex_table(record), encoding="utf-8")

    print(json.dumps(record["hardware"], indent=2))
    print("\npackages found:")
    for package, version in record["packages"].items():
        if version:
            print(f"  {package:<24}{version}")
    missing = [p for p, v in record["packages"].items() if not v]
    if missing:
        print(f"  (not installed: {', '.join(missing)})")
    print(f"\nexperiment runs found: {len(runs)}")
    print(f"embedding caches found: {len(embeddings)}")
    print(f"\ntotals: {json.dumps(record['totals'], indent=2)}")
    print(f"\nwrote {args.output}")
    print(f"wrote {args.latex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
