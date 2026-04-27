"""
Pydantic schemas for the RAG Recommendation API.

Phase 1: Product schemas
  - ProductBase    — shared fields
  - ProductCreate  — used for POST /products (request body)
  - ProductOut     — returned in all responses (adds id)
  - ProductListOut — paginated list envelope
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Core product schema
# ---------------------------------------------------------------------------

class ProductBase(BaseModel):
    """Fields shared between creation and retrieval."""

    name: str = Field(..., min_length=1, max_length=200, description="Product display name")
    category: str = Field(..., min_length=1, max_length=100, description="Top-level category")
    price: float = Field(..., gt=0, description="Price in USD (must be > 0)")
    stock: int = Field(default=0, ge=0, description="Units available in inventory")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Average rating 0–5")
    description: str = Field(..., min_length=1, description="Short product description")
    tags: List[str] = Field(default_factory=list, description="Searchable keyword tags")

    @field_validator("tags", mode="before")
    @classmethod
    def lowercase_tags(cls, v):
        """Normalise tags to lowercase so searches are consistent."""
        return [t.strip().lower() for t in v] if v else []


class ProductCreate(ProductBase):
    """
    Request body for POST /products.

    Optionally accepts a caller-supplied `id`; if omitted the service
    auto-generates one (P<N+1 zero-padded to 3 digits>).
    """

    id: Optional[str] = Field(
        default=None,
        description="Optional caller-supplied ID (e.g. 'P016'). Auto-generated if omitted.",
    )


class ProductOut(ProductBase):
    """Full product representation returned in all API responses."""

    id: str = Field(..., description="Unique product identifier (e.g. 'P001')")

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Response envelopes
# ---------------------------------------------------------------------------

class ProductListOut(BaseModel):
    """Paginated list envelope for GET /products."""

    total: int = Field(..., description="Total number of products in the catalogue")
    count: int = Field(..., description="Number of products in this response")
    products: List[ProductOut]


# ---------------------------------------------------------------------------
# Recommendation schemas (Phase 2 - structured filtering)
# ---------------------------------------------------------------------------

class RecommendRequest(BaseModel):
    """Request body for POST /recommend."""

    query: str = Field(..., min_length=1, description="Natural-language shopping query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum products to return")


class ParsedFiltersOut(BaseModel):
    """Structured filters extracted from the natural-language query."""

    category: Optional[str] = Field(default=None, description="Detected product category")
    min_price: Optional[float] = Field(default=None, description="Detected lower price bound")
    max_price: Optional[float] = Field(default=None, description="Detected upper price bound")


class RecommendResponse(BaseModel):
    """Response envelope for POST /recommend."""

    query: str
    parsed_filters: ParsedFiltersOut
    answer: str
    total: int
    count: int
    top_products: List[ProductOut]
    why_recommended: List[str]
    comparison: List[str]
    products: List[ProductOut]
