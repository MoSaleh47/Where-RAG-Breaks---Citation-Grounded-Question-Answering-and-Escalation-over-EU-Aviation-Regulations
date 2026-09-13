"""Deterministic lineage mapping from legacy flat chunks to E1 parents."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_text(value: str) -> str:
    return " ".join(TOKEN_PATTERN.findall(value.lower()))


def _token_counter(value: str) -> Counter[str]:
    return Counter(TOKEN_PATTERN.findall(value.lower()))


def _similarity(source: str, target: str) -> tuple[float, float]:
    source_counts = _token_counter(source)
    target_counts = _token_counter(target)
    if not source_counts or not target_counts:
        return 0.0, 0.0

    overlap = sum(
        min(source_count, target_counts[token])
        for token, source_count in source_counts.items()
    )
    coverage = overlap / sum(source_counts.values())
    dot = sum(
        source_count * target_counts[token]
        for token, source_count in source_counts.items()
    )
    source_norm = math.sqrt(sum(value * value for value in source_counts.values()))
    target_norm = math.sqrt(sum(value * value for value in target_counts.values()))
    cosine = dot / (source_norm * target_norm)
    return cosine, coverage


def map_legacy_chunks(
    legacy_chunks: Iterable[dict],
    parents: Iterable[dict],
) -> list[dict]:
    """Map chunks using exact containment first and fuzzy ranking only for review."""
    parent_records = list(parents)
    normalized_parents = {
        parent["parent_id"]: normalize_text(parent["text"])
        for parent in parent_records
    }
    parent_by_id = {parent["parent_id"]: parent for parent in parent_records}
    mappings: list[dict] = []

    for chunk in legacy_chunks:
        normalized_chunk = normalize_text(chunk["text"])
        equal_hits = [
            parent_id
            for parent_id, parent_text in normalized_parents.items()
            if normalized_chunk and normalized_chunk == parent_text
        ]
        within_hits = [
            parent_id
            for parent_id, parent_text in normalized_parents.items()
            if normalized_chunk and normalized_chunk in parent_text
        ]
        contains_hits = [
            parent_id
            for parent_id, parent_text in normalized_parents.items()
            if parent_text and parent_text in normalized_chunk
        ]

        method = "fuzzy_review"
        status = "review_required"
        selected_id: str | None = None
        if len(equal_hits) == 1:
            selected_id, method, status = equal_hits[0], "normalized_equal", "auto_mapped"
        elif len(within_hits) == 1:
            selected_id, method, status = (
                within_hits[0],
                "legacy_contained_by_parent",
                "auto_mapped",
            )
        elif len(contains_hits) == 1:
            selected_id, method, status = (
                contains_hits[0],
                "parent_contained_by_legacy",
                "auto_mapped",
            )

        ranked: list[tuple[float, float, float, str]] = []
        for parent in parent_records:
            cosine, coverage = _similarity(chunk["text"], parent["text"])
            combined = 0.3 * cosine + 0.7 * coverage
            ranked.append((combined, cosine, coverage, parent["parent_id"]))
        ranked.sort(reverse=True)

        if selected_id is None:
            selected_id = ranked[0][3]
        selected = next(item for item in ranked if item[3] == selected_id)
        next_best = next((item for item in ranked if item[3] != selected_id), None)
        candidate_ids = [item[3] for item in ranked[:5]]
        selected_parent = parent_by_id[selected_id]

        mappings.append(
            {
                "legacy_chunk_id": chunk["chunk_id"],
                "legacy_citation": chunk.get("citation", ""),
                "legacy_type": chunk.get("type", ""),
                "mapping_status": status,
                "mapping_method": method,
                "parent_id": selected_id,
                "parent_canonical_citation": selected_parent["canonical_citation"],
                "match_score": round(selected[0], 6),
                "cosine_similarity": round(selected[1], 6),
                "source_token_coverage": round(selected[2], 6),
                "score_margin": round(
                    selected[0] - next_best[0] if next_best is not None else selected[0],
                    6,
                ),
                "candidate_parent_ids": ";".join(candidate_ids),
            }
        )

    return mappings
