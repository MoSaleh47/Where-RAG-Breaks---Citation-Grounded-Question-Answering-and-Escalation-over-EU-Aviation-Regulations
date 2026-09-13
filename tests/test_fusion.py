from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.retrieval import reciprocal_rank_fusion  # noqa: E402


def test_rrf_rewards_agreement_between_rankers():
    fused = reciprocal_rank_fusion(
        [["A", "B", "C"], ["C", "B", "D"]],
        constant=60,
        limit=4,
    )
    assert [document_id for document_id, _ in fused] == ["C", "B", "A", "D"]


def test_rrf_skips_duplicate_ids_within_one_ranking():
    fused = reciprocal_rank_fusion([["A", "A", "B"]], constant=0)
    scores = dict(fused)
    assert scores["A"] == 1.0
    assert scores["B"] == pytest.approx(1 / 3)


@pytest.mark.parametrize(
    ("rankings", "constant", "weights", "limit"),
    [
        ([], 60, None, None),
        ([["A"]], -1, None, None),
        ([["A"]], 60, [1, 1], None),
        ([["A"]], 60, [0], None),
        ([["A"]], 60, None, 0),
    ],
)
def test_rrf_rejects_invalid_parameters(rankings, constant, weights, limit):
    with pytest.raises(ValueError):
        reciprocal_rank_fusion(
            rankings, constant=constant, weights=weights, limit=limit
        )
