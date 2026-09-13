"""Build the E1 parent/child corpus and an auditable validation report."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.corpus import build_parent_child_corpus  # noqa: E402
from aviation_rag.corpus.validation import issues_as_dicts, validate_corpus  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--document-version", default="2022-12")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        raise SystemExit(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc)
    corpus = build_parent_child_corpus(source, args.document_version)
    issues, summary = validate_corpus(corpus)

    write_jsonl(output / "parents.jsonl", corpus.parents_as_dicts())
    write_jsonl(output / "children.jsonl", corpus.children_as_dicts())
    (output / "validation.json").write_text(
        json.dumps(
            {"summary": summary, "issues": issues_as_dicts(issues)},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    manifest = {
        "experiment_id": "E1",
        "schema_version": "parent_child_v1",
        "source": str(source),
        "source_sha256": sha256(source),
        "document_version": args.document_version,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "outputs": {
            "parents.jsonl": sha256(output / "parents.jsonl"),
            "children.jsonl": sha256(output / "children.jsonl"),
            "validation.json": sha256(output / "validation.json"),
        },
        "validation_summary": summary,
        "status": "valid" if summary["critical_issue_count"] == 0 else "invalid",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"output={output}")
    return 0 if summary["critical_issue_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

