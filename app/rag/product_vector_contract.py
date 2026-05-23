"""Product vector contract shared by indexing and vector retrieval paths."""

from __future__ import annotations

from typing import Any

from app.models.schema import ProductOut


FILTERABLE_METADATA_FIELDS = frozenset(
    {
        "product_id",
        "category",
        "brand",
        "price",
        "rating",
        "availability",
        "tags",
        "updated_at",
    }
)


def vector_id_for_product(product_id: str) -> str:
    """Map product IDs to stable vector IDs."""
    return f"product:{product_id.strip()}"


def _price_band(price: float) -> str:
    if price < 50:
        return "budget"
    if price < 200:
        return "mid range"
    if price < 500:
        return "premium"
    return "luxury"


def product_embedding_text(product: ProductOut) -> str:
    """Build canonical text used as embedding input for product vectors."""
    tags = ", ".join(product.tags) if product.tags else "general"
    use_cases = ", ".join([product.category, *product.tags[:5]])
    return (
        f"Title: {product.name}\n"
        f"Short description: {product.description}\n"
        f"Category: {product.category}\n"
        "Brand: unspecified\n"
        f"Use cases: {use_cases}\n"
        f"Price band: {_price_band(product.price)}\n"
        f"Special tags: {tags}"
    ).strip()


def product_metadata(product: ProductOut) -> dict[str, Any]:
    """Build Pinecone metadata from the product API schema."""
    availability = "in_stock" if product.stock > 0 else "out_of_stock"
    return {
        "product_id": product.id,
        "name": product.name,
        "category": product.category,
        "brand": "",
        "price": float(product.price),
        "price_band": _price_band(product.price),
        "rating": float(product.rating),
        "availability": availability,
        "tags": list(product.tags),
        "updated_at": "",
    }
