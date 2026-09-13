"""Deterministic rank fusion for hybrid retrieval."""

from __future__ import annotations

from collections import defaultdict


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    *,
    constant: int = 60,
    weights: list[float] | None = None,
    limit: int | None = None,
) -> list[tuple[str, float]]:
    """Fuse ranked document IDs using weighted reciprocal rank fusion.

    Ties are resolved by the best rank in any input and then by document ID,
    keeping results reproducible across platforms.
    """
    if not rankings:
        raise ValueError("At least one ranking is required")
    if constant < 0:
        raise ValueError("constant must be non-negative")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("One weight is required per ranking")
    if any(weight <= 0 for weight in weights):
        raise ValueError("weights must be positive")

    scores: dict[str, float] = defaultdict(float)
    best_rank: dict[str, int] = {}
    for ranking, weight in zip(rankings, weights):
        seen: set[str] = set()
        for rank, document_id in enumerate(ranking, start=1):
            if document_id in seen:
                continue
            seen.add(document_id)
            scores[document_id] += weight / (constant + rank)
            best_rank[document_id] = min(best_rank.get(document_id, rank), rank)

    ordered = sorted(
        scores,
        key=lambda document_id: (-scores[document_id], best_rank[document_id], document_id),
    )
    if limit is not None:
        ordered = ordered[:limit]
    return [(document_id, scores[document_id]) for document_id in ordered]
