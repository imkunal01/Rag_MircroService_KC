"""
routes.py — central router that aggregates all sub-routers.

Mounted under the /api prefix in main.py, so effective paths are:
    /api/products        ← ProductCreate / ProductListOut
    /api/ping            ← health sanity-check
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.products import router as products_router
from app.api.recommendations import router as recommendations_router
from app.rag.generator import gemini_config_status, gemini_live_status

router = APIRouter()

# Sub-routers
router.include_router(products_router)
router.include_router(recommendations_router)


@router.get("/ping", tags=["Health"])
async def ping():
    """Quick sanity-check for the API router."""
    return {"ping": "pong"}


@router.get("/health/gemini", tags=["Health"])
async def gemini_health_config():
    """Check whether Gemini API credentials are configured."""
    return gemini_config_status()


@router.get("/health/gemini/live", tags=["Health"])
async def gemini_health_live(
    timeout_seconds: Annotated[int, Query(ge=2, le=30, description="Timeout for live Gemini ping in seconds")] = 10,
):
    """Check whether Gemini API is reachable with a lightweight live request."""
    return gemini_live_status(timeout_seconds=timeout_seconds)
