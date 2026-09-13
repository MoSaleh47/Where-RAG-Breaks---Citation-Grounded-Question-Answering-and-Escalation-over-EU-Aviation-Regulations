"""Small deterministic BM25 implementation for reproducible lexical retrieval."""

from __future__ import annotations

import math
import re
from collections import Counter

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def lexical_tokens(value: str) -> list[str]:
    return TOKEN_PATTERN.findall(value.lower())


class BM25Index:
    def __init__(
        self,
        documents: list[str],
        document_ids: list[str],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if len(documents) != len(document_ids):
            raise ValueError("Document text and ID counts differ")
        if not documents:
            raise ValueError("At least one document is required")
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("Invalid BM25 parameters")
        self.document_ids = document_ids
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(lexical_tokens(text)) for text in documents]
        self.lengths = [sum(counts.values()) for counts in self.term_frequencies]
        self.average_length = sum(self.lengths) / len(self.lengths)
        document_frequencies: Counter[str] = Counter()
        for counts in self.term_frequencies:
            document_frequencies.update(counts.keys())
        count = len(documents)
        self.idf = {
            term: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequencies.items()
        }

    def rank(self, query: str, limit: int) -> list[tuple[str, float]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_terms = Counter(lexical_tokens(query))
        scores: list[tuple[float, int]] = []
        for index, frequencies in enumerate(self.term_frequencies):
            length = self.lengths[index]
            score = 0.0
            for term, query_frequency in query_terms.items():
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length / self.average_length
                )
                score += (
                    self.idf.get(term, 0.0)
                    * frequency
                    * (self.k1 + 1)
                    / denominator
                    * query_frequency
                )
            scores.append((score, index))
        scores.sort(key=lambda item: (-item[0], item[1]))
        return [
            (self.document_ids[index], score)
            for score, index in scores[: min(limit, len(scores))]
        ]
