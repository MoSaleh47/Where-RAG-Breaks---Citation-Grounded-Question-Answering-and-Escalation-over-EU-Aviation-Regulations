"""Validation rules and summary statistics for parent/child corpora."""

from __future__ import annotations

import collections
from dataclasses import asdict, dataclass

from .parent_child import Corpus


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    record_id: str
    message: str


def validate_corpus(corpus: Corpus) -> tuple[list[ValidationIssue], dict]:
    issues: list[ValidationIssue] = []
    parent_ids = [parent.parent_id for parent in corpus.parents]
    child_ids = [child.child_id for child in corpus.children]
    parent_set = set(parent_ids)

    if not corpus.parents:
        issues.append(ValidationIssue("critical", "empty_corpus", "*", "No parents were extracted"))
    if not corpus.children:
        issues.append(ValidationIssue("critical", "empty_children", "*", "No children were extracted"))

    if len(parent_ids) != len(parent_set):
        issues.append(ValidationIssue("critical", "duplicate_parent_id", "*", "Parent IDs are not unique"))
    if len(child_ids) != len(set(child_ids)):
        issues.append(ValidationIssue("critical", "duplicate_child_id", "*", "Child IDs are not unique"))

    for parent in corpus.parents:
        if not parent.text.strip():
            issues.append(ValidationIssue("critical", "empty_parent", parent.parent_id, "Parent has no text"))
        if not parent.regulation_id:
            issues.append(ValidationIssue("critical", "missing_regulation", parent.parent_id, "Missing regulation identity"))
        if not parent.child_ids:
            issues.append(ValidationIssue("critical", "parent_without_children", parent.parent_id, "No children"))
        if parent.document_type == "ARTICLE" and not parent.title.lower().startswith("article"):
            issues.append(ValidationIssue("critical", "article_title_invalid", parent.parent_id, parent.title))
        is_named_gm_reference = (
            parent.parent_id == "GM_EU_376_2014_ACRONYMS"
            and parent.title.upper() == "LIST OF ACRONYMS"
        )
        if parent.document_type == "GM" and not parent.title[:1].isdigit() and not is_named_gm_reference:
            issues.append(ValidationIssue("warning", "gm_title_unusual", parent.parent_id, parent.title))
        if parent.char_count > 40_000:
            issues.append(ValidationIssue("warning", "very_large_parent", parent.parent_id, str(parent.char_count)))

    children_by_parent: dict[str, list] = collections.defaultdict(list)
    for child in corpus.children:
        children_by_parent[child.parent_id].append(child)
        if child.parent_id not in parent_set:
            issues.append(ValidationIssue("critical", "orphan_child", child.child_id, child.parent_id))
        if not child.text.strip():
            issues.append(ValidationIssue("critical", "empty_child", child.child_id, "Child has no text"))
        if not child.retrieval_text.strip():
            issues.append(ValidationIssue("critical", "empty_retrieval_text", child.child_id, "Missing retrieval text"))
        if child.char_count > 4_000:
            issues.append(ValidationIssue("warning", "large_child", child.child_id, str(child.char_count)))
        if child.unit_type == "table_row" and "|" not in child.text and child.word_count > 20:
            issues.append(ValidationIssue("warning", "table_row_unstructured", child.child_id, child.text[:120]))

    for parent in corpus.parents:
        actual_ids = [child.child_id for child in children_by_parent[parent.parent_id]]
        if actual_ids != parent.child_ids:
            issues.append(
                ValidationIssue("critical", "child_order_mismatch", parent.parent_id, "Parent child IDs differ")
            )

    parent_types = collections.Counter(parent.document_type for parent in corpus.parents)
    document_counts = collections.Counter(parent.document_id for parent in corpus.parents)
    child_types = collections.Counter(child.unit_type for child in corpus.children)
    severity_counts = collections.Counter(issue.severity for issue in issues)
    child_sizes = [child.char_count for child in corpus.children]

    summary = {
        "parent_count": len(corpus.parents),
        "child_count": len(corpus.children),
        "ignored_block_count": corpus.ignored_blocks,
        "parents_by_type": dict(sorted(parent_types.items())),
        "parents_by_document": dict(sorted(document_counts.items())),
        "children_by_type": dict(sorted(child_types.items())),
        "child_char_count": {
            "minimum": min(child_sizes) if child_sizes else 0,
            "maximum": max(child_sizes) if child_sizes else 0,
            "mean": round(sum(child_sizes) / len(child_sizes), 2) if child_sizes else 0,
        },
        "issues_by_severity": dict(sorted(severity_counts.items())),
        "critical_issue_count": severity_counts["critical"],
        "warning_issue_count": severity_counts["warning"],
    }
    return issues, summary


def issues_as_dicts(issues: list[ValidationIssue]) -> list[dict]:
    return [asdict(issue) for issue in issues]

