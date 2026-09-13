"""Rank exact E1 child-evidence candidates for human gold-set review."""

from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "how", "in", "is", "it", "of", "on", "or", "that",
    "the", "their", "this", "to", "under", "was", "what", "when", "where",
    "which", "who", "will", "with",
}


def content_tokens(value: str) -> list[str]:
    return [
        token
        for token in TOKEN_PATTERN.findall(value.lower())
        if token not in STOPWORDS
    ]


def normalize_citation(value: str) -> str:
    tokens = TOKEN_PATTERN.findall(value.lower())
    if tokens and tokens[0] == "section":
        tokens[0] = "gm"
    return " ".join(tokens)


def _lexical_scores(query: str, evidence: str) -> tuple[float, float, float]:
    query_counts = Counter(content_tokens(query))
    evidence_counts = Counter(content_tokens(evidence))
    if not query_counts or not evidence_counts:
        return 0.0, 0.0, 0.0

    overlap = sum(
        min(count, evidence_counts[token])
        for token, count in query_counts.items()
    )
    recall = overlap / sum(query_counts.values())
    precision = overlap / sum(evidence_counts.values())
    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    dot = sum(count * evidence_counts[token] for token, count in query_counts.items())
    qnorm = math.sqrt(sum(count * count for count in query_counts.values()))
    enorm = math.sqrt(sum(count * count for count in evidence_counts.values()))
    cosine = dot / (qnorm * enorm)
    return recall, f1, cosine


def _citation_score(gold: str, candidate: str) -> float:
    gold_norm = normalize_citation(gold)
    candidate_norm = normalize_citation(candidate)
    if not gold_norm or not candidate_norm:
        return 0.0
    if gold_norm == candidate_norm:
        return 1.0
    if candidate_norm.startswith(gold_norm + " ") or gold_norm.startswith(candidate_norm + " "):
        return 0.6
    return 0.0


def rank_child_candidates(
    qa: dict,
    parent_id: str,
    children: list[dict],
    limit: int = 5,
) -> list[dict]:
    query = f"{qa.get('answer', '')} {qa.get('question', '')}"
    ranked: list[tuple[float, float, float, float, float, dict]] = []
    for child in children:
        if child["parent_id"] != parent_id:
            continue
        recall, f1, cosine = _lexical_scores(query, child["text"])
        citation = _citation_score(
            qa.get("citation", ""),
            child.get("canonical_citation", ""),
        )
        score = 0.45 * recall + 0.2 * f1 + 0.2 * cosine + 0.15 * citation
        ranked.append((score, citation, recall, f1, cosine, child))
    ranked.sort(key=lambda item: (-item[0], item[5]["sequence"]))

    candidates: list[dict] = []
    for rank, (score, citation, recall, f1, cosine, child) in enumerate(
        ranked[:limit],
        start=1,
    ):
        candidates.append(
            {
                "rank": rank,
                "child_id": child["child_id"],
                "canonical_citation": child["canonical_citation"],
                "unit_type": child["unit_type"],
                "score": round(score, 6),
                "citation_score": round(citation, 6),
                "query_token_recall": round(recall, 6),
                "token_f1": round(f1, 6),
                "cosine_similarity": round(cosine, 6),
                "text_preview": child["text"][:240],
            }
        )
    return candidates


def review_priority(candidates: list[dict]) -> str:
    if not candidates:
        return "blocking"
    top = candidates[0]
    margin = top["score"] - candidates[1]["score"] if len(candidates) > 1 else top["score"]
    if top["citation_score"] == 1.0 and top["query_token_recall"] >= 0.45:
        return "low"
    if top["query_token_recall"] >= 0.55 and margin >= 0.08:
        return "medium"
    return "high"
