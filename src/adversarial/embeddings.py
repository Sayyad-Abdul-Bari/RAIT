"""
Embedding index for red-team prompts.
Uses Google Gemini Embedding API (models/gemini-embedding-001) via google-genai SDK.
"""
from __future__ import annotations

import os
from typing import List

import numpy as np

from src.adversarial.dataset import AttackPrompt


def _normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v / norm if norm > 0 else v


class EmbeddingIndex:
    """Pre-computes and stores Gemini embeddings for all red-team prompts."""

    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or os.getenv(
            "EMBEDDING_MODEL", "models/gemini-embedding-001"
        )
        self._client = None
        self._prompts: List[AttackPrompt] = []
        self._embeddings: np.ndarray | None = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set in .env")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def build(self, prompts: List[AttackPrompt]) -> None:
        client = self._get_client()
        self._prompts = prompts
        texts = [p.prompt for p in prompts]
        result = client.models.embed_content(
            model=self._model_name,
            contents=texts,
        )
        vecs = np.array([e.values for e in result.embeddings], dtype=np.float32)
        self._embeddings = np.array([_normalize(v) for v in vecs])

    def encode(self, text: str) -> np.ndarray:
        client = self._get_client()
        result = client.models.embed_content(
            model=self._model_name,
            contents=[text],
        )
        return _normalize(np.array(result.embeddings[0].values, dtype=np.float32))

    @property
    def prompts(self) -> List[AttackPrompt]:
        return self._prompts

    @property
    def embeddings(self) -> np.ndarray:
        if self._embeddings is None:
            raise RuntimeError("Call build() first.")
        return self._embeddings

    def is_ready(self) -> bool:
        return self._embeddings is not None
