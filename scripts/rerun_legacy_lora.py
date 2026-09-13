"""Re-run the LoRA baseline over the frozen benchmark, offline and unbilled.

The adapter in ``Documents/lora_model`` is unchanged and decoding is greedy
(``do_sample=False``), so this run is deterministic and costs nothing beyond GPU
time. Two things follow from that, and both are reported:

* the 73 records whose wording did not change should reproduce the stored
  predictions in ``Documents/results_lora.json`` exactly, which makes this run a
  reproducibility check on the historical artefact as well as an extension of it;
* the 25 reworded records get predictions for the first time, so the three-system
  comparison can cover all 98.

No frozen record was in the adapter's training split -- the historical script
held out the seeded 100-question sample, and all 98 frozen records lie inside
it -- so extending to 98 introduces no train/test contamination. The script
re-checks that and refuses to continue if it ever stops being true.

Usage (from ``aviation_rag_research/``)::

    python scripts/rerun_legacy_lora.py \
        --benchmark data/evaluation/reviewed_benchmark_v1/reviewed_benchmark.jsonl \
        --qa-pairs ../Documents/qa_pairs_final.json \
        --adapter ../Documents/lora_model \
        --stored ../Documents/results_lora.json \
        --output experiments/legacy_rerun_frozen98_v1 \
        --check-only

``--check-only`` verifies the data, the contamination property and the
environment, and loads no model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"
VARIANT = "lora-3b"
RANDOM_SEED = 42
HISTORICAL_SAMPLE_SIZE = 100
TRAIN_RATIO = 0.8
MAX_LEN = 512
MAX_NEW_TOKENS = 200

# Copied verbatim from fine_tune_lora.py.
SYSTEM_MSG = (
    "You are a regulatory compliance assistant specialized in EU aviation regulations. "
    "Answer the question concisely and always cite the exact article using format [Article X(Y)] "
    "or [Section X.X] at the end of your answer."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def normalise(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def build_prompt(question: str) -> str:
    return (
        f"<|begin_of_text|>"
        f"<|start_header_id|>system<|end_header_id|>\n{SYSTEM_MSG}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n{question}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--qa-pairs", required=True, type=Path)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--stored", type=Path, help="Historical results_lora.json, for the reproducibility check.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--no-4bit", action="store_true", help="Load in bf16 instead of 4-bit NF4.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--check-only", action="store_true", help="Validate inputs and environment; load no model.")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    frozen = {record["qa_id"]: record for record in read_jsonl(args.benchmark.resolve())}
    pool = json.loads(args.qa_pairs.resolve().read_text(encoding="utf-8"))
    pool_by_id = {item["qa_id"]: item for item in pool}

    # Reproduce the historical sample and training split.
    sample_ids = [item["qa_id"] for item in random.Random(RANDOM_SEED).sample(pool, HISTORICAL_SAMPLE_SIZE)]
    held_out = set(sample_ids)
    train_pool = [item for item in pool if item["qa_id"] not in held_out]
    shuffler = random.Random(RANDOM_SEED)
    shuffler.shuffle(train_pool)
    train_ids = {item["qa_id"] for item in train_pool[: int(len(train_pool) * TRAIN_RATIO)]}

    contaminated = sorted(set(frozen) & train_ids)
    if contaminated:
        raise SystemExit(
            "Refusing to run: these frozen records were in the adapter's training "
            f"split, so their predictions would be memorised, not inferred: {contaminated}"
        )

    ordered = [frozen[qa_id] for qa_id in sample_ids if qa_id in frozen]
    ordered.extend(frozen[qa_id] for qa_id in sorted(set(frozen) - held_out))
    if args.limit:
        ordered = ordered[: args.limit]

    reworded = [
        record["qa_id"]
        for record in ordered
        if normalise(record["question"]) != normalise(pool_by_id.get(record["qa_id"], {}).get("question"))
    ]

    print(f"Frozen records            : {len(ordered)}")
    print(f"In the adapter's training split : {len(contaminated)}")
    print(f"Reworded since the stored run   : {len(reworded)}")
    print(f"Adapter                   : {args.adapter}")
    print(f"Base model                : {args.model_id}")

    stored_by_id: dict[str, str] = {}
    if args.stored and args.stored.exists():
        for record in json.loads(args.stored.resolve().read_text(encoding="utf-8")):
            stored_by_id[record["qa_id"]] = record.get("prediction", "")
        print(f"Stored predictions loaded : {len(stored_by_id)}")

    if args.check_only:
        missing = []
        for module in ("torch", "transformers", "peft"):
            try:
                __import__(module)
            except ImportError:
                missing.append(module)
        print(f"Missing packages          : {missing if missing else 'none'}")
        try:
            import torch  # noqa: PLC0415

            print(f"CUDA available            : {torch.cuda.is_available()}")
        except ImportError:
            pass
        print("\nCheck only: no model was loaded and nothing was written.")
        return 0

    output = args.output.resolve()
    if (output / "results_lora.json").exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite {output / 'results_lora.json'}")

    import torch  # noqa: PLC0415
    from peft import PeftModel  # noqa: PLC0415
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415

    token = None
    for candidate in (Path(".env"), Path("..") / ".env"):
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("HF_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
    import os  # noqa: PLC0415

    token = os.getenv("HF_TOKEN", token)

    tokenizer = AutoTokenizer.from_pretrained(args.model_id, token=token)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    load_kwargs: dict = {"device_map": "auto", "token": token, "torch_dtype": torch.bfloat16}
    if not args.no_4bit:
        from transformers import BitsAndBytesConfig  # noqa: PLC0415

        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    print("\nLoading base model...")
    base = AutoModelForCausalLM.from_pretrained(args.model_id, **load_kwargs)
    model = PeftModel.from_pretrained(base, str(args.adapter.resolve()))
    model.eval()

    results: list[dict] = []
    reproduced = 0
    comparable = 0
    for position, record in enumerate(ordered, start=1):
        prompt = build_prompt(record["question"])
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=MAX_LEN).to(model.device)
        with torch.no_grad():
            generated = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=0.01,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        new_tokens = generated[0][inputs["input_ids"].shape[1] :]
        prediction = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        if record["qa_id"] not in reworded and record["qa_id"] in stored_by_id:
            comparable += 1
            reproduced += int(normalise(prediction) == normalise(stored_by_id[record["qa_id"]]))

        legacy = pool_by_id.get(record["qa_id"], {})
        results.append(
            {
                "system": "lora",
                "variant": VARIANT,
                "qa_id": record["qa_id"],
                "question_type": record.get("question_type", ""),
                "difficulty": record.get("difficulty", ""),
                "question": record["question"],
                "gold_answer": record.get("reference_answer", ""),
                "gold_citation": record.get("acceptable_citation", ""),
                "gold_source_chunk": record.get("legacy_source_chunk", ""),
                "gold_text": legacy.get("gold_text", ""),
                "prediction": prediction,
                "retrieval_success": None,
            }
        )
        print(f"  [{position}/{len(ordered)}] {record['qa_id']}", end="\r")

    output.mkdir(parents=True, exist_ok=True)
    (output / "results_lora.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rate = (reproduced / comparable) if comparable else None
    manifest = {
        "experiment_id": output.name,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Re-run the LoRA baseline over the frozen question wording, covering all frozen records.",
        "inputs": {
            "benchmark_sha256": sha256_file(args.benchmark.resolve()),
            "qa_pairs_sha256": sha256_file(args.qa_pairs.resolve()),
            "adapter_sha256": sha256_file(args.adapter.resolve() / "adapter_model.safetensors"),
            "records": len(ordered),
        },
        "parameters": {
            "base_model": args.model_id,
            "variant": VARIANT,
            "decoding": "greedy, do_sample=False",
            "max_new_tokens": MAX_NEW_TOKENS,
            "max_len": MAX_LEN,
            "quantisation": "bf16" if args.no_4bit else "4-bit NF4, double quant, bf16 compute",
        },
        "contamination_check": {
            "frozen_records_in_training_split": len(contaminated),
        },
        "reproducibility_check": {
            "records_comparable_with_stored_run": comparable,
            "predictions_reproduced_exactly": reproduced,
            "rate": None if rate is None else round(rate, 4),
        },
        "outputs": {"results_lora.json": sha256_file(output / "results_lora.json")},
        "software": {"python": sys.version, "platform": platform.platform()},
    }
    (output / "manifest_lora.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n\nWritten {len(results)} predictions to {output / 'results_lora.json'}")
    if comparable:
        print(f"Reproducibility on unchanged questions: {reproduced}/{comparable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
