"""Dependency-light cosine dense retrieval and gold-evidence metrics."""

from __future__ import annotations

import math

import numpy as np


def normalize_rows(values: np.ndarray) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("Cannot normalize zero-length embedding vectors")
    return matrix / norms


def dense_rank(
    query_embeddings: np.ndarray,
    document_embeddings: np.ndarray,
    document_ids: list[str],
    limit: int,
) -> list[list[tuple[str, float]]]:
    if document_embeddings.shape[0] != len(document_ids):
        raise ValueError("Document ID and embedding counts differ")
    if limit < 1:
        raise ValueError("limit must be positive")
    queries = normalize_rows(query_embeddings)
    documents = normalize_rows(document_embeddings)
    similarities = queries @ documents.T
    top_limit = min(limit, len(document_ids))
    rankings: list[list[tuple[str, float]]] = []
    for row in similarities:
        candidate_indexes = np.argpartition(-row, top_limit - 1)[:top_limit]
        ordered_indexes = candidate_indexes[np.argsort(-row[candidate_indexes])]
        rankings.append(
            [(document_ids[index], float(row[index])) for index in ordered_indexes]
        )
    return rankings


def _dcg(relevances: list[int]) -> float:
    return sum(
        relevance / math.log2(rank + 1)
        for rank, relevance in enumerate(relevances, start=1)
    )


def _acceptable_evidence_sets(record: dict) -> list[set[str]]:
    raw_sets = record.get("acceptable_evidence_sets")
    if raw_sets is None:
        raw_sets = [record.get("gold_child_ids", [])]
    evidence_sets = [set(evidence_set) for evidence_set in raw_sets if evidence_set]
    if not evidence_sets:
        raise ValueError(
            f"{record.get('qa_id', '<unknown>')} has no acceptable evidence set"
        )
    return evidence_sets


def evaluate_rankings(
    qa_records: list[dict],
    rankings: dict[str, list[str]],
    child_parent: dict[str, str],
    k_values: list[int],
) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    for k in sorted(set(k_values)):
        parent_hits = 0
        any_child_hits = 0
        evidence_recall_total = 0.0
        reciprocal_rank_total = 0.0
        ndcg_total = 0.0

        for record in qa_records:
            ranked = rankings[record["qa_id"]][:k]
            evidence_sets = _acceptable_evidence_sets(record)
            acceptable_children = set().union(*evidence_sets)
            acceptable_parents = set(
                record.get("acceptable_parent_ids", [record["parent_id"]])
            )
            retrieved_gold = [
                child_id for child_id in ranked if child_id in acceptable_children
            ]
            if retrieved_gold:
                any_child_hits += 1
                first_rank = next(
                    index
                    for index, child_id in enumerate(ranked, start=1)
                    if child_id in acceptable_children
                )
                reciprocal_rank_total += 1 / first_rank
            retrieved_set = set(retrieved_gold)
            evidence_recall_total += max(
                len(retrieved_set & evidence_set) / len(evidence_set)
                for evidence_set in evidence_sets
            )
            if any(
                child_parent.get(child_id) in acceptable_parents
                for child_id in ranked
            ):
                parent_hits += 1

            relevances = [
                1 if child_id in acceptable_children else 0 for child_id in ranked
            ]
            ideal = [1] * min(len(acceptable_children), k)
            ideal_dcg = _dcg(ideal)
            ndcg_total += _dcg(relevances) / ideal_dcg if ideal_dcg else 0.0

        count = len(qa_records)
        metrics[str(k)] = {
            "n": count,
            "parent_recall": parent_hits / count,
            "any_gold_child_recall": any_child_hits / count,
            "mean_evidence_recall": evidence_recall_total / count,
            "mrr": reciprocal_rank_total / count,
            "ndcg": ndcg_total / count,
        }
    return metrics
