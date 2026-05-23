"""Product indexing pipeline for Pinecone."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.models.schema import ProductOut
from app.rag.embeddings import EmbeddingService
from app.rag.pinecone_store import get_pinecone_store
from app.rag.product_vector_contract import (
    product_embedding_text,
    product_metadata,
    vector_id_for_product,
)
from app.services import product_service


logger = logging.getLogger(__name__)

SyncMode = Literal["full", "incremental"]
STATUS_PATH = Path(__file__).resolve().parents[1] / "data" / "index_sync_status.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_status() -> dict[str, Any]:
    return {
        "last_sync_at": None,
        "mode": None,
        "total_synced_count": 0,
        "failed_ids": [],
        "current_version": None,
        "sync_duration_seconds": 0.0,
        "last_error": None,
        "synced_product_ids": [],
    }


def get_index_status() -> dict[str, Any]:
    """Return the last persisted indexing status."""
    if not STATUS_PATH.exists():
        return _empty_status()

    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read index sync status: %s", exc)
        status = _empty_status()
        status["last_error"] = f"Could not read sync status: {exc}"
        return status


def _save_status(status: dict[str, Any]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")


def _fetch_all_products() -> list[ProductOut]:
    _total, products = product_service.list_products(limit=10000)
    return products


def _build_vector(product: ProductOut, embedding: list[float], version: str, indexed_at: str) -> dict[str, Any]:
    metadata = product_metadata(product)
    metadata["index_version"] = version
    metadata["indexed_at"] = indexed_at
    return {
        "id": vector_id_for_product(product.id),
        "values": embedding,
        "metadata": metadata,
    }


def sync_products(*, mode: SyncMode = "incremental") -> dict[str, Any]:
    """Sync products from the product API into Pinecone and persist status."""
    started = time.perf_counter()
    indexed_at = _utc_now_iso()
    version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    failed_ids: list[str] = []
    synced_ids: list[str] = []

    status = {
        "last_sync_at": indexed_at,
        "mode": mode,
        "total_synced_count": 0,
        "failed_ids": failed_ids,
        "current_version": version,
        "sync_duration_seconds": 0.0,
        "last_error": None,
        "synced_product_ids": synced_ids,
    }

    try:
        products = _fetch_all_products()
        embedder = EmbeddingService()
        store = get_pinecone_store()
        if mode == "full":
            store.clear_namespace()

        vectors: list[dict[str, Any]] = []
        for product in products:
            try:
                document = product_embedding_text(product)
                embedding = embedder.embed_query(document)
                vectors.append(_build_vector(product, embedding, version, indexed_at))
                synced_ids.append(product.id)
            except Exception:
                logger.exception("Failed to build vector for product %s", product.id)
                failed_ids.append(product.id)

        store.upsert(vectors)

        if mode == "incremental":
            previous_ids = set(get_index_status().get("synced_product_ids") or [])
            current_ids = {product.id for product in products}
            for deleted_id in sorted(previous_ids - current_ids):
                try:
                    store.delete_by_product_id(deleted_id)
                except Exception:
                    logger.exception("Failed to delete stale product vector %s", deleted_id)
                    failed_ids.append(deleted_id)

        status["total_synced_count"] = len(synced_ids)
    except Exception as exc:
        logger.exception("Product indexing sync failed")
        status["last_error"] = str(exc)
    finally:
        status["sync_duration_seconds"] = round(time.perf_counter() - started, 3)
        _save_status(status)

    return status
