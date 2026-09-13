from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.retrieval import dense_rank, evaluate_rankings, normalize_rows  # noqa: E402


def test_dense_rank_orders_by_cosine_similarity():
    documents = np.asarray([[1, 0], [0, 1], [1, 1]], dtype=np.float32)
    queries = np.asarray([[1, 0]], dtype=np.float32)
    ranked = dense_rank(queries, documents, ["A", "B", "C"], limit=3)
    assert [item[0] for item in ranked[0]] == ["A", "C", "B"]


def test_normalization_rejects_zero_vectors():
    with pytest.raises(ValueError):
        normalize_rows(np.asarray([[0, 0]], dtype=np.float32))


def test_metrics_separate_parent_and_exact_child_recall():
    records = [
        {
            "qa_id": "Q1",
            "parent_id": "P1",
            "gold_child_ids": ["C1", "C2"],
        },
        {
            "qa_id": "Q2",
            "parent_id": "P2",
            "gold_child_ids": ["C3"],
        },
    ]
    rankings = {
        "Q1": ["C9", "C1", "C2"],
        "Q2": ["C4", "C3", "C8"],
    }
    child_parent = {
        "C1": "P1",
        "C2": "P1",
        "C3": "P2",
        "C4": "P2",
        "C8": "P8",
        "C9": "P9",
    }
    metrics = evaluate_rankings(records, rankings, child_parent, [1, 3])
    assert metrics["1"]["parent_recall"] == 0.5
    assert metrics["1"]["any_gold_child_recall"] == 0.0
    assert metrics["3"]["parent_recall"] == 1.0
    assert metrics["3"]["any_gold_child_recall"] == 1.0
    assert metrics["3"]["mean_evidence_recall"] == 1.0
    assert metrics["3"]["mrr"] == 0.5


def test_document_count_must_match_ids():
    with pytest.raises(ValueError):
        dense_rank(
            np.asarray([[1, 0]], dtype=np.float32),
            np.asarray([[1, 0]], dtype=np.float32),
            [],
            limit=1,
        )


def test_limit_must_be_positive():
    with pytest.raises(ValueError):
        dense_rank(
            np.asarray([[1, 0]], dtype=np.float32),
            np.asarray([[1, 0]], dtype=np.float32),
            ["A"],
            limit=0,
        )


def test_metrics_accept_alternative_evidence_routes_and_parents():
    records = [
        {
            "qa_id": "Q1",
            "parent_id": "P1",
            "gold_child_ids": ["C1", "C2"],
            "acceptable_evidence_sets": [["C1", "C2"], ["C3"]],
            "acceptable_parent_ids": ["P1", "P3"],
        }
    ]
    rankings = {"Q1": ["C3"]}
    child_parent = {"C1": "P1", "C2": "P1", "C3": "P3"}
    metrics = evaluate_rankings(records, rankings, child_parent, [1])
    assert metrics["1"]["parent_recall"] == 1.0
    assert metrics["1"]["any_gold_child_recall"] == 1.0
    assert metrics["1"]["mean_evidence_recall"] == 1.0
    assert metrics["1"]["mrr"] == 1.0
    assert metrics["1"]["ndcg"] == 1.0


def test_metrics_reject_retained_record_without_evidence():
    records = [{"qa_id": "Q1", "parent_id": "P1", "gold_child_ids": []}]
    with pytest.raises(ValueError, match="no acceptable evidence"):
        evaluate_rankings(records, {"Q1": []}, {}, [1])
