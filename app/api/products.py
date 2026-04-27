"""
products.py — API router for /products endpoints.

Endpoints
---------
GET  /products          List products (with optional filters & pagination)
GET  /products/{id}     Fetch a single product by ID
POST /products          Add a new product to the catalogue
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.models.schema import ProductCreate, ProductListOut, ProductOut
from app.services import product_service
from app.services.product_service import ProductSourceUnavailableError

router = APIRouter(prefix="/products", tags=["Products"])


# ---------------------------------------------------------------------------
# GET /products
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=ProductListOut,
    summary="List products",
    description=(
        "Returns the full product catalogue. "
        "Supports optional filtering by **category**, **tag**, and **price range**, "
        "plus **skip/limit** pagination."
    ),
)
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category (case-insensitive)"),
    tag: Optional[str] = Query(None, description="Filter by tag (case-insensitive)"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price (inclusive)"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price (inclusive)"),
    skip: int = Query(0, ge=0, description="Number of records to skip (offset)"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return (page size)"),
):
    try:
        total, products = product_service.list_products(
            category=category,
            tag=tag,
            min_price=min_price,
            max_price=max_price,
            skip=skip,
            limit=limit,
        )
    except ProductSourceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return ProductListOut(total=total, count=len(products), products=products)


# ---------------------------------------------------------------------------
# GET /products/{product_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{product_id}",
    response_model=ProductOut,
    summary="Get product by ID",
    description="Fetch a single product by its unique identifier (e.g. `P001`).",
)
async def get_product(product_id: str):
    try:
        product = product_service.get_product(product_id)
    except ProductSourceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found.",
        )
    return product


# ---------------------------------------------------------------------------
# POST /products
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new product",
    description=(
        "Adds a new product to the catalogue and persists it to **products.json**. "
        "If `id` is omitted, one is auto-generated (e.g. `P016`)."
    ),
)
async def create_product(payload: ProductCreate):
    try:
        product = product_service.add_product(payload)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return product
