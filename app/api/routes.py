"""
routes.py — central router that aggregates all sub-routers.

Mounted under the /api prefix in main.py, so effective paths are:
    /api/products        ← ProductCreate / ProductListOut
    /api/ping            ← health sanity-check
"""

from fastapi import APIRouter

from app.api.products import router as products_router
from app.api.recommendations import router as recommendations_router

router = APIRouter()

# Sub-routers
router.include_router(products_router)
router.include_router(recommendations_router)


@router.get("/ping", tags=["Health"])
async def ping():
    """Quick sanity-check for the API router."""
    return {"ping": "pong"}
