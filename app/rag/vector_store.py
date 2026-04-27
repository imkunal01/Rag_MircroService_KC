"""
RAG — Vector store interface.

Phase 3: FAISS-backed in-memory vector search.

Uses cosine similarity via inner product over normalized vectors.
Falls back to numpy similarity if FAISS is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
	import numpy as np
except Exception:  # pragma: no cover - optional dependency
	np = None

try:
	import faiss
except Exception:  # pragma: no cover - fallback path for minimal envs
	faiss = None


@dataclass
class SearchHit:
	"""Single vector search match."""

	item_id: str
	score: float


class ProductVectorStore:
	"""In-memory vector index for product semantic retrieval."""

	def __init__(self, dim: int):
		self.dim = dim
		self._ids: list[str] = []
		self._matrix: list[list[float]] = []
		self._index = faiss.IndexFlatIP(dim) if (faiss is not None and np is not None) else None

	def clear(self) -> None:
		self._ids = []
		self._matrix = []
		if self._index is not None:
			self._index.reset()

	def add(self, item_ids: Iterable[str], embeddings: Iterable[Iterable[float]]) -> None:
		ids = list(item_ids)
		matrix = [list(map(float, row)) for row in embeddings]

		if len(matrix) != len(ids):
			raise ValueError("Number of embeddings must match number of ids")

		if matrix and any(len(row) != self.dim for row in matrix):
			raise ValueError("Embedding dimension mismatch")

		self._ids = ids
		self._matrix = matrix

		if self._index is not None:
			self._index.reset()
			self._index.add(np.array(self._matrix, dtype=np.float32))

	def search(self, query_embedding: Iterable[float], k: int) -> list[SearchHit]:
		"""Return top-k highest similarity matches."""
		if not self._ids or k <= 0:
			return []

		top_k = min(k, len(self._ids))
		query = list(map(float, query_embedding))
		if len(query) != self.dim:
			raise ValueError("Query embedding dimension mismatch")

		if self._index is not None:
			scores, indices = self._index.search(np.array([query], dtype=np.float32), top_k)
			return [
				SearchHit(item_id=self._ids[idx], score=float(score))
				for score, idx in zip(scores[0], indices[0])
				if idx >= 0
			]

		similarities = [sum(a * b for a, b in zip(row, query)) for row in self._matrix]
		order = sorted(range(len(similarities)), key=lambda idx: similarities[idx], reverse=True)[:top_k]
		return [SearchHit(item_id=self._ids[idx], score=float(similarities[idx])) for idx in order]
