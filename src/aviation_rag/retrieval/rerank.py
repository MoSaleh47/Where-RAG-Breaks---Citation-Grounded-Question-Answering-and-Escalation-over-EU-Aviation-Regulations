"""Utilities for deterministic reranking of a fixed candidate set."""

from __future__ import annotations


def rerank_from_scores(
    candidate_ids: list[str],
    scores: list[float],
    *,
    limit: int | None = None,
) -> list[tuple[str, float, int]]:
    """Sort candidates by score with stable, deterministic tie breaking."""
    if len(candidate_ids) != len(scores):
        raise ValueError("Candidate and score counts differ")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Candidate IDs must be unique")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    ranked = sorted(
        (
            (candidate_id, float(score), original_rank)
            for original_rank, (candidate_id, score) in enumerate(
                zip(candidate_ids, scores), start=1
            )
        ),
        key=lambda item: (-item[1], item[2], item[0]),
    )
    return ranked if limit is None else ranked[:limit]
