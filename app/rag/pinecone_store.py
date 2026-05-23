"""Pinecone storage wrapper for product recommendation vectors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from app.core.config import PineconeSettings

try:
    from pinecone import Pinecone, ServerlessSpec
except Exception:  # pragma: no cover - optional dependency until Phase A install
    Pinecone = None
    ServerlessSpec = None


logger = logging.getLogger(__name__)


class PineconeStoreError(RuntimeError):
    """Raised when Pinecone cannot be configured or reached safely."""


@dataclass(frozen=True)
class PineconeSearchHit:
    """Single Pinecone vector search match."""

    vector_id: str
    score: float
    metadata: dict[str, Any]


class PineconeProductStore:
    """Small boundary around all Pinecone SDK operations."""

    def __init__(self, settings: PineconeSettings, dimension: int, metric: str = "cosine"):
        self.settings = settings
        self.dimension = dimension
        self.metric = metric
        self._client: Any = None
        self._index: Any = None

    def init(self) -> None:
        """Connect to Pinecone and create or validate the configured index."""
        if Pinecone is None or ServerlessSpec is None:
            raise PineconeStoreError(
                "Pinecone SDK is not installed. Install the pinecone dependency."
            )

        self._client = Pinecone(api_key=self.settings.api_key)
        self._ensure_index()
        self._index = self._client.Index(self.settings.index_name)
        self._validate_index_dimension()
        logger.info(
            "Pinecone index ready",
            extra={
                "index": self.settings.index_name,
                "namespace": self.settings.namespace,
                "dimension": self.dimension,
            },
        )

    def upsert(self, vectors: Iterable[dict[str, Any]]) -> None:
        """Upsert vectors into the configured namespace."""
        index = self._require_index()
        vector_list = list(vectors)
        if not vector_list:
            return
        index.upsert(vectors=vector_list, namespace=self.settings.namespace)

    def query(
        self,
        vector: list[float],
        *,
        top_k: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[PineconeSearchHit]:
        """Query product vectors from the configured namespace."""
        index = self._require_index()
        if len(vector) != self.dimension:
            raise PineconeStoreError(
                f"Query vector dimension {len(vector)} does not match index dimension {self.dimension}."
            )

        response = index.query(
            vector=vector,
            top_k=top_k or self.settings.top_k_default,
            namespace=self.settings.namespace,
            filter=metadata_filter,
            include_metadata=True,
        )
        matches = getattr(response, "matches", None)
        if matches is None and isinstance(response, dict):
            matches = response.get("matches", [])

        hits: list[PineconeSearchHit] = []
        for match in matches or []:
            if isinstance(match, dict):
                hits.append(
                    PineconeSearchHit(
                        vector_id=str(match.get("id", "")),
                        score=float(match.get("score", 0.0)),
                        metadata=dict(match.get("metadata") or {}),
                    )
                )
            else:
                hits.append(
                    PineconeSearchHit(
                        vector_id=str(getattr(match, "id", "")),
                        score=float(getattr(match, "score", 0.0)),
                        metadata=dict(getattr(match, "metadata", {}) or {}),
                    )
                )
        return hits

    def delete_by_product_id(self, product_id: str) -> None:
        """Delete a product vector by product ID."""
        index = self._require_index()
        index.delete(
            filter={"product_id": {"$eq": product_id}},
            namespace=self.settings.namespace,
        )

    def clear_namespace(self) -> None:
        """Delete every vector in the configured namespace."""
        index = self._require_index()
        index.delete(delete_all=True, namespace=self.settings.namespace)

    def update_by_product_id(self, product_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        """Replace a product vector by product ID."""
        from app.rag.product_vector_contract import vector_id_for_product

        if len(vector) != self.dimension:
            raise PineconeStoreError(
                f"Product vector dimension {len(vector)} does not match index dimension {self.dimension}."
            )
        self.upsert(
            [
                {
                    "id": vector_id_for_product(product_id),
                    "values": vector,
                    "metadata": metadata,
                }
            ]
        )

    def health_check(self) -> dict[str, Any]:
        """Return Pinecone dependency health details."""
        try:
            if self._index is None:
                self.init()
            stats = self._require_index().describe_index_stats()
            namespaces = self._extract_namespaces(stats)
            namespace_stats = namespaces.get(self.settings.namespace, {})
            return {
                "status": "healthy",
                "index": self.settings.index_name,
                "namespace": self.settings.namespace,
                "dimension": self.dimension,
                "namespace_vector_count": namespace_stats.get("vector_count", 0),
            }
        except Exception as exc:
            logger.exception("Pinecone health check failed")
            return {
                "status": "unhealthy",
                "index": self.settings.index_name,
                "namespace": self.settings.namespace,
                "error": str(exc),
            }

    def _ensure_index(self) -> None:
        index_names = self._list_index_names()
        if self.settings.index_name in index_names:
            return

        self._client.create_index(
            name=self.settings.index_name,
            dimension=self.dimension,
            metric=self.metric,
            spec=ServerlessSpec(
                cloud=self.settings.cloud,
                region=self.settings.region,
            ),
        )

    def _validate_index_dimension(self) -> None:
        description = self._client.describe_index(self.settings.index_name)
        actual_dimension = self._extract_dimension(description)
        if actual_dimension is None:
            raise PineconeStoreError("Could not verify Pinecone index dimension.")
        if int(actual_dimension) != self.dimension:
            raise PineconeStoreError(
                f"Pinecone index dimension {actual_dimension} does not match embedding dimension {self.dimension}."
            )

    def _list_index_names(self) -> set[str]:
        response = self._client.list_indexes()
        if hasattr(response, "names"):
            return set(response.names())
        if isinstance(response, dict):
            return {str(item.get("name")) for item in response.get("indexes", []) if item.get("name")}
        return {str(item.name) for item in response if getattr(item, "name", None)}

    @staticmethod
    def _extract_dimension(description: Any) -> int | None:
        if isinstance(description, dict):
            return description.get("dimension")
        return getattr(description, "dimension", None)

    @staticmethod
    def _extract_namespaces(stats: Any) -> dict[str, dict[str, Any]]:
        if isinstance(stats, dict):
            return dict(stats.get("namespaces") or {})
        return dict(getattr(stats, "namespaces", {}) or {})

    def _require_index(self) -> Any:
        if self._index is None:
            raise PineconeStoreError("Pinecone store has not been initialized.")
        return self._index


_store: PineconeProductStore | None = None


def get_pinecone_store() -> PineconeProductStore:
    """Return a process-wide Pinecone store instance."""
    global _store
    if _store is None:
        from app.rag.embeddings import EmbeddingService

        settings = PineconeSettings.from_env()
        dimension = EmbeddingService().dimension
        _store = PineconeProductStore(settings=settings, dimension=dimension)
    return _store
