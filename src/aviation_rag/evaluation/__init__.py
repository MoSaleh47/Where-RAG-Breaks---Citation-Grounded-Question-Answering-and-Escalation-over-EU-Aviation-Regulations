"""Evaluation-set lineage and scoring utilities."""

from .child_mapping import rank_child_candidates, review_priority
from .citations import (
    Citation,
    ParentResolver,
    exact_citation_match,
    legacy_citation_match,
    parent_citation_match,
    parse_citations,
)
from .review import (
    ReviewValidationError,
    apply_review_decisions,
    validate_review_rows,
)
from .legacy_mapping import map_legacy_chunks, normalize_text
from .splitting import assert_group_disjoint, stable_grouped_split

__all__ = [
    "Citation",
    "ParentResolver",
    "ReviewValidationError",
    "exact_citation_match",
    "legacy_citation_match",
    "parent_citation_match",
    "parse_citations",
    "apply_review_decisions",
    "validate_review_rows",
    "assert_group_disjoint",
    "map_legacy_chunks",
    "normalize_text",
    "rank_child_candidates",
    "review_priority",
    "stable_grouped_split",
]
