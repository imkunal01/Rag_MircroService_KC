"""Admin endpoints for Pinecone indexing operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import get_admin_api_key
from app.services.indexing_service import get_index_status, sync_products


router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_admin(x_admin_api_key: str | None = Header(default=None)) -> None:
    expected = get_admin_api_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY is not configured.",
        )
    if x_admin_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key.",
        )


@router.post("/reindex", summary="Run a full Pinecone product reindex")
async def reindex(_: None = Depends(_require_admin)):
    return sync_products(mode="full")


@router.post("/sync", summary="Run an incremental Pinecone product sync")
async def incremental_sync(_: None = Depends(_require_admin)):
    return sync_products(mode="incremental")


@router.get("/index-status", summary="Get last Pinecone indexing status")
async def index_status(_: None = Depends(_require_admin)):
    return get_index_status()
