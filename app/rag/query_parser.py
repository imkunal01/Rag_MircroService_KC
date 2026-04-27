"""
query_parser.py - Phase 2 structured query parsing.

Extracts simple constraints from natural language:
* category
* min_price
* max_price

This module intentionally avoids AI/LLM usage and relies on regex + keyword rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass
class ParsedQuery:
    """Normalized filters extracted from a user query."""

    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None


_CATEGORY_ALIASES = {
    "Electronics": [
        "electronics",
        "electronic",
        "phone",
        "phones",
        "mobile",
        "mobiles",
        "smartphone",
        "smartphones",
        "headphone",
        "headphones",
        "earbud",
        "earbuds",
        "speaker",
        "speakers",
        "keyboard",
        "webcam",
        "charger",
    ],
    "Furniture": ["furniture", "chair", "chairs", "desk", "desks", "table", "tables"],
    "Home & Office": ["home", "office", "home office", "lamp", "lighting"],
    "Wearables": ["wearable", "wearables", "fitness", "tracker", "watch", "smartwatch"],
    "Accessories": ["accessory", "accessories", "stand", "dock", "docking"],
    "Networking": ["network", "networking", "wifi", "wi-fi", "router", "mesh"],
}

_MAX_PRICE_PATTERNS = [
    re.compile(r"\b(?:under|below|less\s+than|cheaper\s+than|up\s*to|upto|max(?:imum)?|<=)\s*[₹$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|thousand)?\b"),
]

_MIN_PRICE_PATTERNS = [
    re.compile(r"\b(?:above|over|more\s+than|greater\s+than|min(?:imum)?|>=|at\s+least)\s*[₹$]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|thousand)?\b"),
]


def _to_number(raw_value: str, magnitude: str) -> float:
    """Convert extracted numeric text to a float, supporting shorthand like 20k."""
    value = float(raw_value.replace(",", ""))
    if magnitude in {"k", "thousand"}:
        value *= 1000
    return value


def _extract_price(text: str, patterns: list[re.Pattern[str]]) -> Optional[float]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            number = match.group(1)
            magnitude = (match.group(2) or "").lower()
            return _to_number(number, magnitude)
    return None


def _extract_category(text: str, categories: Sequence[str]) -> Optional[str]:
    category_lookup = {c.lower(): c for c in categories}

    # Prefer exact category mentions from the catalogue first.
    for normalized, original in category_lookup.items():
        if normalized and normalized in text:
            return original

    # Fall back to keyword aliases.
    for canonical, aliases in _CATEGORY_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases):
            if canonical.lower() in category_lookup:
                return category_lookup[canonical.lower()]
            return canonical

    return None


def parse_query(query: str, known_categories: Sequence[str]) -> ParsedQuery:
    """Parse natural-language query into structured filters."""
    lowered = query.lower().strip()

    max_price = _extract_price(lowered, _MAX_PRICE_PATTERNS)
    min_price = _extract_price(lowered, _MIN_PRICE_PATTERNS)
    category = _extract_category(lowered, known_categories)

    # Guardrail: if conflicting bounds are extracted, drop both.
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = None, None

    return ParsedQuery(
        category=category,
        min_price=min_price,
        max_price=max_price,
    )
