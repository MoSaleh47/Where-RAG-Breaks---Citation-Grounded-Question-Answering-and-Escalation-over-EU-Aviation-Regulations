"""Create an evidence-linked, AI-assisted audit candidate from Legacy-100."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.evaluation import rank_child_candidates  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def proposed_evidence(qa: dict, parent_id: str, children: list[dict]) -> list[str]:
    selected: list[str] = []
    overall = rank_child_candidates(qa, parent_id, children, limit=6)
    if overall:
        selected.append(overall[0]["child_id"])

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", qa.get("answer", ""))
        if sentence.strip()
    ]
    for sentence in sentences:
        sentence_qa = {
            "question": qa.get("question", ""),
            "answer": sentence,
            "citation": qa.get("citation", ""),
        }
        candidates = rank_child_candidates(sentence_qa, parent_id, children, limit=1)
        if candidates and candidates[0]["score"] >= 0.12:
            selected.append(candidates[0]["child_id"])

    for candidate in overall:
        if candidate["citation_score"] == 1.0:
            selected.append(candidate["child_id"])

    return list(dict.fromkeys(selected))[:6]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa", required=True, type=Path)
    parser.add_argument("--legacy-results", required=True, type=Path)
    parser.add_argument("--qa-parent-map", required=True, type=Path)
    parser.add_argument("--children", required=True, type=Path)
    parser.add_argument("--overrides", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    qa_path = args.qa.resolve()
    results_path = args.legacy_results.resolve()
    mapping_path = args.qa_parent_map.resolve()
    children_path = args.children.resolve()
    overrides_path = args.overrides.resolve()

    qa_records = json.loads(qa_path.read_text(encoding="utf-8"))
    qa_by_id = {record["qa_id"]: record for record in qa_records}
    result_records = json.loads(results_path.read_text(encoding="utf-8"))
    legacy_ids = {record["qa_id"] for record in result_records}
    if len(legacy_ids) != 100:
        raise SystemExit(f"Expected 100 unique Legacy-100 IDs, found {len(legacy_ids)}")

    mappings = {
        row["qa_id"]: row
        for row in read_csv(mapping_path)
        if row["qa_id"] in legacy_ids
    }
    children = read_jsonl(children_path)
    child_by_id = {child["child_id"]: child for child in children}
    overrides = {row["qa_id"]: row for row in read_csv(overrides_path)}
    if unknown := sorted(set(overrides) - legacy_ids):
        raise SystemExit(f"Overrides outside Legacy-100: {unknown}")

    audited: list[dict] = []
    for qa_id in sorted(legacy_ids):
        source_qa = qa_by_id[qa_id]
        mapping = mappings[qa_id]
        parent_id = mapping["parent_id"]
        override = overrides.get(qa_id)

        if override and override["decision"] == "exclude":
            decision = "excluded_invalid"
            evidence_ids: list[str] = []
            question = source_qa["question"]
            answer = source_qa["answer"]
            citation = source_qa.get("citation", "")
            notes = override["review_notes"]
        elif override and override["decision"] == "rewrite":
            decision = "ai_rewritten_supported"
            evidence_ids = [
                value
                for value in override["gold_child_ids"].split(";")
                if value
            ]
            question = override["corrected_question"]
            answer = override["corrected_answer"]
            citation = override["corrected_citation"]
            notes = override["review_notes"]
        else:
            decision = "ai_provisional_supported"
            evidence_ids = proposed_evidence(source_qa, parent_id, children)
            question = source_qa["question"]
            answer = source_qa["answer"]
            citation = source_qa.get("citation", "")
            notes = "AI-assisted evidence proposal; independent human review pending."

        for child_id in evidence_ids:
            if child_id not in child_by_id:
                raise SystemExit(f"Unknown evidence ID for {qa_id}: {child_id}")
            if child_by_id[child_id]["parent_id"] != parent_id:
                raise SystemExit(
                    f"Evidence parent mismatch for {qa_id}: {child_id} versus {parent_id}"
                )
        if decision != "excluded_invalid" and not evidence_ids:
            raise SystemExit(f"No evidence proposed for retained record {qa_id}")

        audited.append(
            {
                "qa_id": qa_id,
                "legacy_source_chunk": source_qa["source_chunk"],
                "parent_id": parent_id,
                "gold_child_ids": evidence_ids,
                "question": question,
                "reference_answer": answer,
                "acceptable_citation": citation,
                "question_type": source_qa.get("question_type", ""),
                "difficulty": source_qa.get("difficulty", ""),
                "audit_decision": decision,
                "source_record_changed": bool(
                    override and override["decision"] == "rewrite"
                ),
                "independent_human_review": False,
                "audit_notes": notes,
            }
        )

    jsonl_path = output / "legacy100_ai_audited.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in audited:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    exceptions = [
        record
        for record in audited
        if record["audit_decision"] != "ai_provisional_supported"
    ]
    exception_path = output / "exceptions_for_independent_review.csv"
    fields = [
        "qa_id",
        "audit_decision",
        "parent_id",
        "gold_child_ids",
        "question",
        "reference_answer",
        "acceptable_citation",
        "audit_notes",
    ]
    with exception_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in exceptions:
            row = dict(record)
            row["gold_child_ids"] = ";".join(record["gold_child_ids"])
            writer.writerow(row)

    counts = Counter(record["audit_decision"] for record in audited)
    summary = {
        "input_count": len(audited),
        "retained_count": sum(
            record["audit_decision"] != "excluded_invalid" for record in audited
        ),
        "decision_counts": dict(sorted(counts.items())),
        "independent_human_review_complete": False,
        "status": "ai_assisted_candidate_not_final_gold",
        "inputs": {
            "qa_sha256": sha256(qa_path),
            "legacy_results_sha256": sha256(results_path),
            "qa_parent_map_sha256": sha256(mapping_path),
            "children_sha256": sha256(children_path),
            "overrides_sha256": sha256(overrides_path),
        },
        "outputs": {
            "audited_jsonl_sha256": sha256(jsonl_path),
            "exception_csv_sha256": sha256(exception_path),
        },
    }
    (output / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
