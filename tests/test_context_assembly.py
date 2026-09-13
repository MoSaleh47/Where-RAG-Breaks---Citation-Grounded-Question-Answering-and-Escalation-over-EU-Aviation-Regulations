from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.generation import ContextSelectionConfig, build_context_bundle  # noqa: E402


def fixtures():
    parents = {
        "P1": {
            "parent_id": "P1",
            "child_ids": ["C1", "C2", "C3"],
            "document_id": "DOC1",
            "document_type": "ARTICLE",
            "document_version": "v1",
            "hierarchy_path": ["Regulation", "Article 1"],
        },
        "P2": {
            "parent_id": "P2",
            "child_ids": ["C4"],
            "document_id": "DOC1",
            "document_type": "ANNEX",
            "document_version": "v1",
            "hierarchy_path": ["Regulation", "Annex"],
        },
    }
    children = {}
    for sequence, child_id in enumerate(["C1", "C2", "C3"], start=1):
        children[child_id] = {
            "child_id": child_id,
            "parent_id": "P1",
            "sequence": sequence,
            "canonical_citation": f"Article 1({sequence})",
            "unit_type": "paragraph",
            "text": f"Evidence text {child_id}",
            "word_count": 3,
        }
    children["C4"] = {
        "child_id": "C4",
        "parent_id": "P2",
        "sequence": 1,
        "canonical_citation": "Annex, item 1",
        "unit_type": "list_item",
        "text": "Separate annex evidence",
        "word_count": 3,
    }
    return children, parents


def test_context_selects_ranked_anchors_without_gold_labels():
    children, parents = fixtures()
    bundle = build_context_bundle(
        question="What is required?",
        ranked_child_ids=["C2", "C4", "C1"],
        children_by_id=children,
        parents_by_id=parents,
        config=ContextSelectionConfig(top_k=2, max_words=20),
    )
    assert bundle["allowed_source_ids"] == ["C2", "C4"]
    assert bundle["stats"]["anchor_count"] == 2
    assert "[SOURCE C2]" in bundle["prompt_context"]


def test_context_adds_neighbours_after_preserving_anchor_budget():
    children, parents = fixtures()
    bundle = build_context_bundle(
        question="What is required?",
        ranked_child_ids=["C2", "C4"],
        children_by_id=children,
        parents_by_id=parents,
        config=ContextSelectionConfig(top_k=2, max_words=12, neighbor_radius=1),
    )
    assert set(bundle["allowed_source_ids"]) == {"C1", "C2", "C3", "C4"}
    assert bundle["stats"]["anchor_count"] == 2
    assert bundle["stats"]["neighbor_count"] == 2


def test_context_can_limit_dominance_by_one_parent():
    children, parents = fixtures()
    bundle = build_context_bundle(
        question="What is required?",
        ranked_child_ids=["C1", "C2", "C4"],
        children_by_id=children,
        parents_by_id=parents,
        config=ContextSelectionConfig(
            top_k=2,
            max_words=20,
            max_per_parent=1,
        ),
    )
    assert bundle["allowed_source_ids"] == ["C1", "C4"]


@pytest.mark.parametrize(
    "config",
    [
        ContextSelectionConfig(top_k=0),
        ContextSelectionConfig(max_words=0),
        ContextSelectionConfig(neighbor_radius=-1),
        ContextSelectionConfig(max_per_parent=0),
    ],
)
def test_context_rejects_invalid_configuration(config):
    children, parents = fixtures()
    with pytest.raises(ValueError):
        build_context_bundle(
            question="Question",
            ranked_child_ids=["C1"],
            children_by_id=children,
            parents_by_id=parents,
            config=config,
        )


def test_context_rejects_duplicate_ranked_ids():
    children, parents = fixtures()
    with pytest.raises(ValueError):
        build_context_bundle(
            question="Question",
            ranked_child_ids=["C1", "C1"],
            children_by_id=children,
            parents_by_id=parents,
        )
