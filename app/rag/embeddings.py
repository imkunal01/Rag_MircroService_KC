"""
RAG — Embedding utilities.

Phase 3: semantic embeddings.

Primary path:
* sentence-transformers model for semantic vectors

Fallback path:
* deterministic hashed bag-of-words embedding so local development still works
  even when heavyweight ML packages are unavailable.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

try:
	from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - fallback path for minimal envs
	SentenceTransformer = None


_TOKEN_EXPANSIONS = {
	"camera": ["webcam", "photo", "video", "lens"],
	"gaming": ["game", "rgb", "mechanical", "performance"],
	"battery": ["power", "charging", "rechargeable", "wireless"],
	"phone": ["mobile", "smartphone", "wireless", "charger"],
	"phones": ["mobile", "smartphone", "wireless", "charger"],
}


class EmbeddingService:
	"""Small wrapper for text embedding generation."""

	def __init__(self, model_name: str = "all-MiniLM-L6-v2", fallback_dim: int = 384):
		self.model_name = model_name
		self.fallback_dim = fallback_dim
		self._model = None

		if SentenceTransformer is not None:
			self._model = SentenceTransformer(model_name)

	@property
	def dimension(self) -> int:
		"""Embedding vector size used by the current backend."""
		if self._model is not None:
			return int(self._model.get_sentence_embedding_dimension())
		return self.fallback_dim

	def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
		"""Return L2-normalized embeddings as list-of-lists."""
		text_list = list(texts)
		if not text_list:
			return []

		if self._model is not None:
			vectors = self._model.encode(
				text_list,
				normalize_embeddings=True,
				convert_to_numpy=False,
			)
			return [list(map(float, vec)) for vec in vectors]

		vectors = [self._fallback_embed(text) for text in text_list]
		return [self._normalize_vector(vec) for vec in vectors]

	def embed_query(self, query: str) -> list[float]:
		"""Return a single normalized embedding vector for a query."""
		return self.embed_texts([query])[0]

	def _fallback_embed(self, text: str) -> list[float]:
		"""Deterministic hashed embedding when sentence-transformers is unavailable."""
		vec = [0.0] * self.fallback_dim
		tokens = re.findall(r"[a-z0-9]+", text.lower())
		if not tokens:
			return vec

		for token in tokens:
			for expanded in [token, *_TOKEN_EXPANSIONS.get(token, [])]:
				digest = hashlib.sha256(expanded.encode("utf-8")).hexdigest()
				idx = int(digest[:8], 16) % self.fallback_dim
				vec[idx] += 1.0
		return vec

	@staticmethod
	def _normalize_vector(vector: list[float]) -> list[float]:
		norm = math.sqrt(sum(v * v for v in vector))
		if norm == 0:
			return vector
		return [v / norm for v in vector]
