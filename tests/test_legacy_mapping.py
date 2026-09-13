from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.evaluation import map_legacy_chunks, normalize_text  # noqa: E402


def parent(parent_id: str, text: str, citation: str = "Article 1") -> dict:
    return {
        "parent_id": parent_id,
        "text": text,
        "canonical_citation": citation,
    }


def chunk(chunk_id: str, text: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "citation": "legacy",
        "type": "ARTICLE",
    }


def test_normalization_removes_formatting_without_changing_word_order():
    assert normalize_text("Article 4(1)(a) ? Test") == "article 4 1 a test"


def test_equal_content_is_automatically_mapped():
    mappings = map_legacy_chunks(
        [chunk("C1", "The same legal text.")],
        [parent("P1", "The same legal text.")],
    )
    assert mappings[0]["parent_id"] == "P1"
    assert mappings[0]["mapping_status"] == "auto_mapped"
    assert mappings[0]["mapping_method"] == "normalized_equal"


def test_split_legacy_chunk_maps_to_its_containing_parent():
    mappings = map_legacy_chunks(
        [chunk("C1", "mandatory reporting obligation")],
        [
            parent(
                "P1",
                "Context before mandatory reporting obligation and context after.",
            ),
            parent("P2", "unrelated confidentiality rule"),
        ],
    )
    assert mappings[0]["parent_id"] == "P1"
    assert mappings[0]["mapping_method"] == "legacy_contained_by_parent"


def test_fuzzy_candidate_is_not_silently_accepted():
    mappings = map_legacy_chunks(
        [chunk("C1", "reporting safety occurrence")],
        [
            parent("P1", "safety reporting for an occurrence"),
            parent("P2", "confidential personal information"),
        ],
    )
    assert mappings[0]["parent_id"] == "P1"
    assert mappings[0]["mapping_status"] == "review_required"
    assert mappings[0]["mapping_method"] == "fuzzy_review"


def test_candidates_are_ranked_and_auditable():
    mappings = map_legacy_chunks(
        [chunk("C1", "alpha beta gamma")],
        [parent("P1", "alpha beta delta"), parent("P2", "zeta eta theta")],
    )
    assert mappings[0]["candidate_parent_ids"].split(";")[0] == "P1"
    assert mappings[0]["source_token_coverage"] > 0
