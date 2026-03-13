"""
Semantic search: match an incoming query to known red-team attack patterns
using cosine similarity. Catches rephrased attacks that regex misses.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from src.adversarial.dataset import AttackPrompt
from src.adversarial.embeddings import EmbeddingIndex

DEFAULT_THRESHOLD = 0.65  # cosine similarity; tuned to minimise false positives


@dataclass
class SearchResult:
    query: str
    matched_prompt: Optional[AttackPrompt]
    similarity: float
    is_attack: bool

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "matched_id": self.matched_prompt.id if self.matched_prompt else None,
            "matched_category": self.matched_prompt.category if self.matched_prompt else None,
            "similarity": round(self.similarity, 4),
            "is_attack": self.is_attack,
        }


class SemanticSearcher:
    """
    Cosine similarity search against the pre-built embedding index.
    Threshold 0.65 chosen to balance precision (avoid false alarms on benign
    queries that use similar vocabulary) vs recall (catch clever rephrasing).
    """

    def __init__(self, index: EmbeddingIndex, threshold: float = DEFAULT_THRESHOLD):
        self._index = index
        self._threshold = threshold

    def search(self, query: str) -> SearchResult:
        query_vec = self._index.encode(query)
        sims = self._index.embeddings @ query_vec  # dot product = cosine (normalised)

        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])

        if best_sim >= self._threshold:
            return SearchResult(
                query=query,
                matched_prompt=self._index.prompts[best_idx],
                similarity=best_sim,
                is_attack=True,
            )
        return SearchResult(
            query=query,
            matched_prompt=None,
            similarity=best_sim,
            is_attack=False,
        )

    def batch_search(self, queries: List[str]) -> List[SearchResult]:
        return [self.search(q) for q in queries]
