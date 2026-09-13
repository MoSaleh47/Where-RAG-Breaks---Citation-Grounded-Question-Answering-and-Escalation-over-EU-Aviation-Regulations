"""Run evidence-constrained generation over a prepared context set (E5).

The model receives only the SOURCE blocks selected by retrieval. It must attach
every claim to a supplied ``source_id`` and to a verbatim quote from that source,
and it may not write display citations -- those are resolved by the application
from the source identifier. Both rules come from D019 and both are checked
deterministically afterwards by ``verify_answer``.

Two guards matter for the thesis and are enforced here rather than trusted:

* **Split discipline.** ``--split development`` is the default. Running on the
  held-out split requires ``--split test`` *and* ``--i-have-frozen-calibration``,
  so the test partition cannot be touched by an absent-minded re-run while
  thresholds are still being tuned.
* **Schema conformance.** The request uses the API's strict structured-output
  mode, built from the project's own schema, and the response is then re-checked
  against that schema locally. A model that satisfies the API but violates the
  project contract is still recorded as a failure.

Every response is cached on disk by a key covering the model, prompt, schema and
context. Re-running costs nothing and never re-bills for work already done.

Usage:

    python scripts/run_generation.py \\
        --contexts experiments/E5_context_top5_reviewed_v1/contexts.jsonl \\
        --prompt prompts/evidence_constrained_answer_v1.md \\
        --schema schemas/answer_output_v1.schema.json \\
        --output experiments/E5_generation_top5_dev_v1 \\
        --cache experiments/cache/generation \\
        --model gpt-4o-mini --split development
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.generation import verify_answer  # noqa: E402

SECTION_SPLIT = re.compile(r"^## ", re.MULTILINE)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_prompt(path: Path) -> tuple[str, str]:
    """Split the prompt file into its system instruction and user template."""
    text = path.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    for block in SECTION_SPLIT.split(text):
        title, _, body = block.partition("\n")
        sections[title.strip().lower()] = body.strip()
    system = sections.get("system instruction")
    template = sections.get("user message template")
    if not system or not template:
        raise SystemExit(
            f"{path} must contain '## System instruction' and '## User message template'"
        )
    return system, template


def strict_schema(schema: dict) -> dict:
    """Convert the project schema into the API's strict structured-output dialect.

    The canonical schema stays untouched on disk; only the request copy is
    adapted. Strict mode rejects ``oneOf`` and ignores length keywords, so those
    are rewritten or dropped here -- and the response is validated again against
    the canonical contract afterwards, so nothing is weakened by the conversion.
    """
    def convert(node):
        if isinstance(node, list):
            return [convert(item) for item in node]
        if not isinstance(node, dict):
            return node
        node = {
            key: value
            for key, value in node.items()
            if key not in {"minLength", "maxLength", "minItems", "maxItems"}
        }
        if "oneOf" in node:
            branches = node.pop("oneOf")
            types: list[str] = []
            enum_values: list = []
            for branch in branches:
                branch_type = branch.get("type")
                if isinstance(branch_type, str):
                    types.append(branch_type)
                if "enum" in branch:
                    enum_values.extend(branch["enum"])
                    types.append("string")
            if enum_values:
                if "null" in types:
                    enum_values = [None, *enum_values]
                node["type"] = sorted(set(types)) if len(set(types)) > 1 else types[0]
                node["enum"] = enum_values
            else:
                node["type"] = sorted(set(types))
        if node.get("type") == "object" or "properties" in node:
            node.setdefault("additionalProperties", False)
            if "properties" in node:
                node["required"] = list(node["properties"])
        return {key: convert(value) for key, value in node.items()}

    converted = convert(copy.deepcopy(schema))
    converted.pop("$schema", None)
    converted.pop("$id", None)
    return converted


def build_user_message(template: str, context: dict) -> str:
    return (
        template.replace("{question}", context["question"])
        .replace("{allowed_source_ids}", "\n".join(context["allowed_source_ids"]))
        .replace("{prompt_context}", context["prompt_context"])
    )


def cache_key(model: str, system: str, user: str, schema_hash: str) -> str:
    payload = json.dumps(
        {"model": model, "system": system, "user": user, "schema": schema_hash},
        sort_keys=True,
    ).encode("utf-8")
    return sha256_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contexts", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--split",
        default="development",
        choices=("development", "test", "all"),
        help="Which partition to generate for. Defaults to development.",
    )
    parser.add_argument(
        "--i-have-frozen-calibration",
        action="store_true",
        help=(
            "Required to generate on the held-out split. Pass this only once "
            "verifier and abstention thresholds are fixed on development data."
        ),
    )
    parser.add_argument("--limit", type=int, help="Generate only the first N records (smoke test).")
    parser.add_argument("--dry-run", action="store_true", help="Build requests, call nothing.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.split in ("test", "all") and not args.i_have_frozen_calibration:
        raise SystemExit(
            f"Refusing to generate on '{args.split}': the held-out split is only "
            "scored once, after calibration is frozen on development data. "
            "Re-run with --i-have-frozen-calibration if that is genuinely done."
        )

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")

    contexts = read_jsonl(args.contexts.resolve())
    if args.split != "all":
        contexts = [record for record in contexts if record["split"] == args.split]
    if args.limit:
        contexts = contexts[: args.limit]
    if not contexts:
        raise SystemExit(f"No context records for split '{args.split}'")

    system_instruction, user_template = load_prompt(args.prompt.resolve())
    canonical_schema = json.loads(args.schema.resolve().read_text(encoding="utf-8"))
    request_schema = strict_schema(canonical_schema)
    schema_hash = sha256_file(args.schema.resolve())

    requests = [
        (record, build_user_message(user_template, record)) for record in contexts
    ]

    if args.dry_run:
        record, user_message = requests[0]
        print(f"split={args.split}  records={len(requests)}  model={args.model}")
        print(f"\n--- system ---\n{system_instruction}")
        print(f"\n--- user (first record, {record['qa_id']}) ---\n{user_message[:1500]}")
        print(f"\n--- request schema ---\n{json.dumps(request_schema, indent=2)[:900]}")
        return 0

    from dotenv import load_dotenv
    from openai import OpenAI, __version__ as openai_version

    load_dotenv(WORKSPACE_ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not configured")
    client = OpenAI()

    cache_dir = args.cache.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    cache_hits = 0
    resolved_models: set[str] = set()

    for index, (record, user_message) in enumerate(requests, start=1):
        key = cache_key(args.model, system_instruction, user_message, schema_hash)
        cached_path = cache_dir / f"{key}.json"
        if cached_path.exists():
            envelope = json.loads(cached_path.read_text(encoding="utf-8"))
            cache_hits += 1
        else:
            response = client.chat.completions.create(
                model=args.model,
                temperature=args.temperature,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_message},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "answer_output_v1",
                        "strict": True,
                        "schema": request_schema,
                    },
                },
            )
            choice = response.choices[0]
            envelope = {
                "content": choice.message.content,
                "refusal": getattr(choice.message, "refusal", None),
                "finish_reason": choice.finish_reason,
                "resolved_model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }
                if response.usage
                else {},
            }
            cached_path.write_text(
                json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8"
            )
            print(f"generated {index}/{len(requests)}  {record['qa_id']}", flush=True)

        for field in usage:
            usage[field] += envelope.get("usage", {}).get(field, 0)
        if envelope.get("resolved_model"):
            resolved_models.add(envelope["resolved_model"])

        payload = None
        parse_error = None
        if envelope.get("content"):
            try:
                payload = json.loads(envelope["content"])
            except json.JSONDecodeError as error:
                parse_error = str(error)

        evidence_by_id = {source["source_id"]: source for source in record["sources"]}
        verification = (
            verify_answer(payload, evidence_by_id)
            if payload is not None
            else {
                "decision": "retry_or_abstain",
                "structural_pass": False,
                "quote_pass": False,
                "schema_errors": [parse_error or "no content returned"],
                "quote_errors": [],
                "supported_claim_ids": [],
                "resolved_citations": [],
                "semantic_verification_required": False,
            }
        )
        results.append(
            {
                "qa_id": record["qa_id"],
                "split": record["split"],
                "question": record["question"],
                "allowed_source_ids": record["allowed_source_ids"],
                "answer": payload,
                "parse_error": parse_error,
                "refusal": envelope.get("refusal"),
                "finish_reason": envelope.get("finish_reason"),
                "verification": verification,
            }
        )

    answers_path = output / "answers.jsonl"
    answers_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in results),
        encoding="utf-8",
    )

    abstained = [r for r in results if (r["answer"] or {}).get("abstain") is True]
    summary = {
        "status": "generated_on_frozen_reviewed_benchmark",
        "split": args.split,
        "record_count": len(results),
        "model_requested": args.model,
        "model_resolved": sorted(resolved_models),
        "temperature": args.temperature,
        "cache_hits": cache_hits,
        "api_calls": len(results) - cache_hits,
        "usage_tokens": usage,
        "schema_conformance": {
            "parse_failures": sum(1 for r in results if r["parse_error"]),
            "refusals": sum(1 for r in results if r["refusal"]),
            "schema_violations": sum(
                1 for r in results if not r["verification"]["structural_pass"]
            ),
        },
        "verification": {
            "structural_pass": sum(
                1 for r in results if r["verification"]["structural_pass"]
            ),
            "quote_pass": sum(1 for r in results if r["verification"]["quote_pass"]),
            "quote_pass_strict": sum(
                1 for r in results if r["verification"].get("quote_pass_strict")
            ),
            "answers_with_elided_quotes": sum(
                1 for r in results if r["verification"].get("elided_quotes")
            ),
            "quote_span_total": sum(
                len(support)
                for r in results
                for claim in ((r["answer"] or {}).get("claims") or [])
                for support in [claim.get("supports") or []]
            ),
            "both_pass": sum(
                1
                for r in results
                if r["verification"]["structural_pass"] and r["verification"]["quote_pass"]
            ),
            "decisions": dict(
                Counter(r["verification"]["decision"] for r in results)
            ),
        },
        "abstention": {
            "count": len(abstained),
            "reasons": dict(
                Counter(r["answer"]["abstention_reason"] for r in abstained)
            ),
        },
        "note": (
            "Structural and quote verification are deterministic. They establish "
            "that a claim points at a supplied source and reproduces its wording "
            "exactly; they do not establish that the source supports the claim. "
            "Semantic support remains a separate question."
        ),
    }
    summary_path = output / "generation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    manifest = {
        "experiment_id": output.name,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "generated_on_frozen_reviewed_benchmark",
        "inputs": {
            "contexts_sha256": sha256_file(args.contexts.resolve()),
            "prompt_sha256": sha256_file(args.prompt.resolve()),
            "schema_sha256": schema_hash,
        },
        "parameters": {
            "model_requested": args.model,
            "model_resolved": sorted(resolved_models),
            "temperature": args.temperature,
            "split": args.split,
        },
        "outputs": {
            "answers_sha256": sha256_file(answers_path),
            "generation_summary_sha256": sha256_file(summary_path),
        },
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "openai": openai_version,
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())