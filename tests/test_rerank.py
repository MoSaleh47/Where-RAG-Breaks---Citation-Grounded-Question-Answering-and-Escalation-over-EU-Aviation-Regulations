from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.retrieval import rerank_from_scores  # noqa: E402


def test_rerank_orders_by_score_and_preserves_original_rank_for_ties():
    ranked = rerank_from_scores(
        ["A", "B", "C"],
        [0.1, 0.8, 0.8],
    )
    assert ranked == [("B", 0.8, 2), ("C", 0.8, 3), ("A", 0.1, 1)]


def test_rerank_applies_limit():
    ranked = rerank_from_scores(["A", "B"], [0.1, 0.2], limit=1)
    assert ranked == [("B", 0.2, 2)]


@pytest.mark.parametrize(
    ("candidate_ids", "scores", "limit"),
    [
        (["A"], [], None),
        (["A", "A"], [0.2, 0.1], None),
        (["A"], [0.1], 0),
    ],
)
def test_rerank_rejects_invalid_inputs(candidate_ids, scores, limit):
    with pytest.raises(ValueError):
        rerank_from_scores(candidate_ids, scores, limit=limit)
