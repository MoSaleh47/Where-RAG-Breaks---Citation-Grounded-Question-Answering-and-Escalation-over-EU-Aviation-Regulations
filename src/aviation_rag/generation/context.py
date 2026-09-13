"""Deterministic evidence-context assembly from reranked child units."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ContextSelectionConfig:
    top_k: int = 5
    max_words: int = 1200
    neighbor_radius: int = 0
    max_per_parent: int | None = None

    def validate(self) -> None:
        if self.top_k < 1:
            raise ValueError("top_k must be positive")
        if self.max_words < 1:
            raise ValueError("max_words must be positive")
        if self.neighbor_radius < 0:
            raise ValueError("neighbor_radius must be non-negative")
        if self.max_per_parent is not None and self.max_per_parent < 1:
            raise ValueError("max_per_parent must be positive")


def _context_source(
    child: dict,
    parent: dict,
    *,
    role: str,
    retrieval_rank: int,
    anchor_id: str,
) -> dict:
    return {
        "source_id": child["child_id"],
        "parent_id": child["parent_id"],
        "role": role,
        "anchor_id": anchor_id,
        "retrieval_rank": retrieval_rank,
        "sequence": child["sequence"],
        "canonical_citation": child["canonical_citation"],
        "document_id": parent["document_id"],
        "document_type": parent["document_type"],
        "document_version": parent["document_version"],
        "hierarchy_path": parent["hierarchy_path"],
        "unit_type": child["unit_type"],
        "text": child["text"],
        "word_count": child["word_count"],
    }


def _format_sources(sources: Iterable[dict]) -> str:
    sections: list[str] = []
    for source in sources:
        hierarchy = " > ".join(source["hierarchy_path"])
        sections.append(
            "\n".join(
                [
                    f"[SOURCE {source['source_id']}]",
                    f"Citation: {source['canonical_citation']}",
                    f"Document: {source['document_id']} ({source['document_type']})",
                    f"Version: {source['document_version']}",
                    f"Hierarchy: {hierarchy}",
                    f"Evidence: {source['text']}",
                ]
            )
        )
    return "\n\n".join(sections)


def build_context_bundle(
    *,
    question: str,
    ranked_child_ids: list[str],
    children_by_id: dict[str, dict],
    parents_by_id: dict[str, dict],
    config: ContextSelectionConfig | None = None,
) -> dict:
    """Build a bounded source bundle without consulting gold evidence."""
    selection = config or ContextSelectionConfig()
    selection.validate()
    if not question.strip():
        raise ValueError("question must not be blank")
    if len(ranked_child_ids) != len(set(ranked_child_ids)):
        raise ValueError("ranked child IDs must be unique")

    parent_counts: dict[str, int] = {}
    anchors: list[tuple[dict, int]] = []
    skipped_for_budget: list[str] = []
    total_words = 0
    for rank, child_id in enumerate(ranked_child_ids, start=1):
        if len(anchors) >= selection.top_k:
            break
        if child_id not in children_by_id:
            raise KeyError(f"Unknown child ID: {child_id}")
        child = children_by_id[child_id]
        parent_id = child["parent_id"]
        if parent_id not in parents_by_id:
            raise KeyError(f"Unknown parent ID: {parent_id}")
        if (
            selection.max_per_parent is not None
            and parent_counts.get(parent_id, 0) >= selection.max_per_parent
        ):
            continue
        child_words = int(child["word_count"])
        if anchors and total_words + child_words > selection.max_words:
            skipped_for_budget.append(child_id)
            continue
        anchors.append((child, rank))
        parent_counts[parent_id] = parent_counts.get(parent_id, 0) + 1
        total_words += child_words

    child_ids_by_parent: dict[str, list[str]] = {}
    for parent_id, parent in parents_by_id.items():
        child_ids_by_parent[parent_id] = list(parent["child_ids"])

    selected: dict[str, dict] = {}
    anchor_order: dict[str, int] = {}
    for child, rank in anchors:
        parent = parents_by_id[child["parent_id"]]
        selected[child["child_id"]] = _context_source(
            child,
            parent,
            role="anchor",
            retrieval_rank=rank,
            anchor_id=child["child_id"],
        )
        anchor_order[child["child_id"]] = rank

    if selection.neighbor_radius:
        for child, rank in anchors:
            sibling_ids = child_ids_by_parent[child["parent_id"]]
            index = sibling_ids.index(child["child_id"])
            lower = max(0, index - selection.neighbor_radius)
            upper = min(len(sibling_ids), index + selection.neighbor_radius + 1)
            for neighbor_id in sibling_ids[lower:upper]:
                if neighbor_id in selected:
                    continue
                neighbor = children_by_id[neighbor_id]
                neighbor_words = int(neighbor["word_count"])
                if total_words + neighbor_words > selection.max_words:
                    skipped_for_budget.append(neighbor_id)
                    continue
                selected[neighbor_id] = _context_source(
                    neighbor,
                    parents_by_id[neighbor["parent_id"]],
                    role="neighbor",
                    retrieval_rank=rank,
                    anchor_id=child["child_id"],
                )
                anchor_order[neighbor_id] = rank
                total_words += neighbor_words

    sources = sorted(
        selected.values(),
        key=lambda source: (
            anchor_order[source["source_id"]],
            source["parent_id"],
            source["sequence"],
            source["source_id"],
        ),
    )
    return {
        "question": question,
        "sources": sources,
        "allowed_source_ids": [source["source_id"] for source in sources],
        "prompt_context": _format_sources(sources),
        "selection": {
            "top_k": selection.top_k,
            "max_words": selection.max_words,
            "neighbor_radius": selection.neighbor_radius,
            "max_per_parent": selection.max_per_parent,
        },
        "stats": {
            "anchor_count": sum(source["role"] == "anchor" for source in sources),
            "neighbor_count": sum(source["role"] == "neighbor" for source in sources),
            "source_count": len(sources),
            "evidence_words": total_words,
            "skipped_for_budget": skipped_for_budget,
        },
    }
