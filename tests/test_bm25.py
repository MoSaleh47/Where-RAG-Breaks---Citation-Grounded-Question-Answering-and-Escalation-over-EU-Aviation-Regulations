from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aviation_rag.retrieval import BM25Index, lexical_tokens  # noqa: E402


def test_tokens_preserve_legal_numbers():
    assert lexical_tokens("Article 4(6)(a)") == ["article", "4", "6", "a"]


def test_bm25_ranks_matching_legal_text_first():
    index = BM25Index(
        [
            "Article 4 mandatory occurrence reporting",
            "Article 16 protection of information source",
            "Annex risk classification",
        ],
        ["A", "B", "C"],
    )
    ranked = index.rank("Who must make a mandatory occurrence report?", 3)
    assert ranked[0][0] == "A"


def test_ties_are_deterministic():
    index = BM25Index(["same text", "same text"], ["A", "B"])
    assert [item[0] for item in index.rank("unknown", 2)] == ["A", "B"]


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        BM25Index([], [])
    with pytest.raises(ValueError):
        BM25Index(["one"], [])
    with pytest.raises(ValueError):
        BM25Index(["one"], ["A"], b=1.5)


def test_invalid_limit_is_rejected():
    index = BM25Index(["one"], ["A"])
    with pytest.raises(ValueError):
        index.rank("one", 0)
