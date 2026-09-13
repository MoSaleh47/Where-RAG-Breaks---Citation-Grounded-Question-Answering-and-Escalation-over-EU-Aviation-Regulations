from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.evaluation import assert_group_disjoint, stable_grouped_split  # noqa: E402


def records() -> list[dict]:
    return [
        {"qa_id": "Q1", "parent_id": "P1"},
        {"qa_id": "Q2", "parent_id": "P1"},
        {"qa_id": "Q3", "parent_id": "P2"},
        {"qa_id": "Q4", "parent_id": "P3"},
        {"qa_id": "Q5", "parent_id": "P4"},
    ]


def test_split_is_deterministic_and_contains_both_views():
    first = stable_grouped_split(records(), seed="fixed")
    second = stable_grouped_split(records(), seed="fixed")
    assert first == second
    assert set(first.values()) == {"development", "test"}


def test_parent_groups_never_cross_splits():
    assignments = stable_grouped_split(records(), seed="fixed")
    assert assignments["Q1"] == assignments["Q2"]
    assert_group_disjoint(records(), assignments)


def test_leakage_assertion_rejects_split_parent():
    assignments = {
        "Q1": "development",
        "Q2": "test",
        "Q3": "test",
        "Q4": "test",
        "Q5": "test",
    }
    with pytest.raises(ValueError, match="leak"):
        assert_group_disjoint(records(), assignments)


def test_invalid_fraction_is_rejected():
    with pytest.raises(ValueError):
        stable_grouped_split(records(), development_fraction=1.0)


def test_one_group_is_not_splittable():
    with pytest.raises(ValueError):
        stable_grouped_split(
            [{"qa_id": "Q1", "parent_id": "P1"}],
        )
