"""product_service.py — remote product source service.

This service uses PRODUCTS_API_URL as the only source of truth.
No local products.json fallback is used.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import List, Optional
from urllib import error, request

from app.models.schema import ProductCreate, ProductOut

_PRODUCTS_API_URL = os.getenv("PRODUCTS_API_URL")
_PRODUCTS_API_TIMEOUT_SECONDS = float(os.getenv("PRODUCTS_API_TIMEOUT_SECONDS", "2.0"))
_PRODUCTS_SYNC_INTERVAL_SECONDS = float(os.getenv("PRODUCTS_SYNC_INTERVAL_SECONDS", "30"))

_products: List[dict] = []
_last_remote_sync_ts: float = 0.0
logger = logging.getLogger(__name__)

_CATEGORY_HINTS: dict[str, set[str]] = {
    "Electronics": {"phone", "mobile", "charger", "inverter", "battery", "led", "tv", "camera"},
    "Appliances": {"fan", "exhaust", "ac", "cooler", "heater", "mixer", "kettle", "fridge"},
    "Home & Office": {"desk", "chair", "lamp", "office", "storage", "organizer", "furniture"},
    "Accessories": {"cable", "case", "cover", "adapter", "mount", "stand"},
}


class ProductSourceUnavailableError(RuntimeError):
    """Raised when the external product source cannot be reached."""


def _coerce_product_dict(item: dict) -> Optional[dict]:
    """Validate and normalize a product payload item from external source."""
    try:
        product = ProductOut(**item)
    except Exception:
        return None
    return product.model_dump()


def _extract_category(item: dict) -> str:
    """Extract category from alternate upstream fields."""
    raw_category = item.get("category")
    if isinstance(raw_category, dict):
        return raw_category.get("name") or "Uncategorized"
    if isinstance(item.get("Category"), dict):
        return item["Category"].get("name") or "Uncategorized"
    if isinstance(raw_category, str) and raw_category.strip():
        return raw_category.strip()
    return "Uncategorized"


def _infer_category_from_text(tags: list[str], name: str) -> str:
    """Infer a stable category when upstream category metadata is missing."""
    tokens = set(re.findall(r"[a-z0-9]+", " ".join(tags + [name]).lower()))
    if not tokens:
        return "Uncategorized"

    best_category = "Uncategorized"
    best_score = 0
    for category, hints in _CATEGORY_HINTS.items():
        score = len(tokens & hints)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def _normalize_external_item(item: dict, *, index: int) -> dict:
    """Map heterogeneous upstream product fields to ProductOut-compatible shape."""
    raw_tags = item.get("tags")
    tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []

    name = str(item.get("name") or "Unnamed Product")
    category = _extract_category(item)
    if category == "Uncategorized":
        category = _infer_category_from_text(tags, name)

    raw_description = item.get("description")
    description = raw_description.strip() if isinstance(raw_description, str) and raw_description.strip() else "No description available."

    price = item.get("price")
    if price is None:
        price = item.get("retailer_price")

    normalized = {
        "id": str(item.get("id") or item.get("_id") or item.get("slug") or f"EXT-{index}"),
        "name": name,
        "category": str(category),
        "price": float(price) if price is not None else 0.0,
        "stock": int(item.get("stock") or 0),
        "rating": float(item.get("rating") or item.get("average_rating") or 0.0),
        "description": description,
        "tags": tags,
    }
    return normalized


def _fetch_remote_products() -> Optional[List[dict]]:
    """Fetch products from external backend API and normalize response shape."""
    if not _PRODUCTS_API_URL:
        logger.error("PRODUCTS_API_URL is not set. Cannot fetch products from external API.")
        return None

    req = request.Request(_PRODUCTS_API_URL, method="GET")
    try:
        with request.urlopen(req, timeout=_PRODUCTS_API_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except (error.HTTPError, error.URLError, TimeoutError, ValueError) as exc:
        logger.error("Failed to connect to external product API '%s': %s", _PRODUCTS_API_URL, exc)
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON received from external product API '%s': %s", _PRODUCTS_API_URL, exc)
        return None

    # Accept either a raw list or common envelope keys from upstream services.
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("products"), list):
        items = payload["products"]
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items = payload["items"]
    else:
        logger.error("External product API '%s' returned unsupported payload shape.", _PRODUCTS_API_URL)
        return None

    normalized: List[dict] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, dict):
            mapped = _normalize_external_item(item, index=index)
            parsed = _coerce_product_dict(mapped)
            if parsed is not None:
                normalized.append(parsed)
    return normalized


def _refresh_from_remote_if_needed(force: bool = False) -> None:
    """Sync products from external API at most once per configured interval."""
    global _products, _last_remote_sync_ts
    now = time.time()
    if not force and now - _last_remote_sync_ts < _PRODUCTS_SYNC_INTERVAL_SECONDS:
        return

    remote_products = _fetch_remote_products()
    _last_remote_sync_ts = now
    if remote_products is not None:
        _products = remote_products
        return

    # Remote is unavailable and no cache exists yet.
    if not _products:
        raise ProductSourceUnavailableError("External product API is unavailable.")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def list_products(
    *,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[int, List[ProductOut]]:
    """
    Return (total_matching, paginated_page) after optional filtering.

    Parameters
    ----------
    category  : case-insensitive exact match on product.category
    tag       : products whose tags list contains this value (case-insensitive)
    min_price : inclusive lower bound on price
    max_price : inclusive upper bound on price
    skip      : offset for pagination
    limit     : page size (max items to return)
    """
    _refresh_from_remote_if_needed()
    results = _products

    if category:
        results = [p for p in results if p["category"].lower() == category.lower()]

    if tag:
        results = [p for p in results if tag.lower() in [t.lower() for t in p.get("tags", [])]]

    if min_price is not None:
        results = [p for p in results if p["price"] >= min_price]

    if max_price is not None:
        results = [p for p in results if p["price"] <= max_price]

    total = len(results)
    page = results[skip : skip + limit]

    return total, [ProductOut(**item) for item in page]


def get_product(product_id: str) -> Optional[ProductOut]:
    """Return a single product by its ID, or None if not found."""
    _refresh_from_remote_if_needed()
    for p in _products:
        if p["id"].upper() == product_id.upper():
            return ProductOut(**p)
    return None


def add_product(payload: ProductCreate) -> ProductOut:
    """Create operation is not supported by this service in remote-only mode."""
    raise NotImplementedError("POST /api/products is disabled. Use your external products backend API.")


def get_categories() -> List[str]:
    """Return unique categories currently present in the catalogue."""
    _refresh_from_remote_if_needed()
    seen = set()
    categories: List[str] = []
    for product in _products:
        category = product.get("category")
        if isinstance(category, str) and category not in seen:
            seen.add(category)
            categories.append(category)
    return categories
