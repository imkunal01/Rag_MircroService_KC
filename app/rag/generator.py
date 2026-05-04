"""
LLM generation layer for recommendation answers.

Design goals:
* Grounded generation: only use retrieved products as source of truth
* Low hallucination: explicit constraints in prompt
* Safe fallback: deterministic answer when Gemini/env is unavailable
"""

from __future__ import annotations

import json
import os
from urllib import error, request

from app.models.schema import ProductOut
from app.utils.helpers import chunk_by_char_budget, truncate_text


_SYSTEM_PROMPT = (
    "You are a product recommendation assistant. "
    "Use ONLY the provided product context. "
    "Do not invent specs or products. "
    "If context is insufficient, say so clearly."
)


def _build_product_context(products: list[ProductOut], *, max_items: int = 6, max_chars: int = 3200) -> str:
    rows: list[str] = []
    for i, product in enumerate(products[:max_items], start=1):
        row = {
            "rank": i,
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "price": product.price,
            "rating": product.rating,
            "stock": product.stock,
            "description": truncate_text(product.description, 220),
            "tags": product.tags,
        }
        rows.append(json.dumps(row, ensure_ascii=True))

    return "\n".join(chunk_by_char_budget(rows, max_chars))


def _fallback_answer(query: str, products: list[ProductOut]) -> str:
    if not products:
        return "I could not find matching products for your query with the current filters."

    best = products[0]
    alternatives = ", ".join(product.name for product in products[1:3])
    if alternatives:
        return (
            f"Best match is {best.name} because it aligns with '{query}', has rating {best.rating:.1f}/5, "
            f"and fits the retrieved constraints. You can also consider {alternatives}."
        )
    return (
        f"Best match is {best.name} because it aligns with '{query}', has rating {best.rating:.1f}/5, "
        "and is the strongest option among retrieved products."
    )


def _call_gemini(prompt: str, *, timeout_seconds: int = 20) -> str:
    """Call Gemini generateContent API and return plain text output."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ""

    model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 220,
        },
    }
    body = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except (error.HTTPError, error.URLError, TimeoutError):
        return ""

    try:
        parsed = json.loads(raw)
        candidates = parsed.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return " ".join(t.strip() for t in texts if t.strip())
    except (json.JSONDecodeError, AttributeError, IndexError, TypeError):
        return ""


def gemini_config_status() -> dict:
    """Return whether Gemini credentials are configured."""
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    configured = bool(api_key and api_key.strip())
    return {
        "provider": "gemini",
        "model": model,
        "configured": configured,
        "message": "Gemini API key is configured." if configured else "GEMINI_API_KEY is missing.",
    }


def gemini_live_status(*, timeout_seconds: int = 10) -> dict:
    """Perform a lightweight live ping against Gemini and report status."""
    status = gemini_config_status()
    if not status["configured"]:
        status["working"] = False
        return status

    text = _call_gemini("Reply with OK.", timeout_seconds=timeout_seconds)
    if text:
        status["working"] = True
        status["message"] = "Gemini API responded successfully."
        status["response_preview"] = truncate_text(text, 80)
    else:
        status["working"] = False
        status["message"] = "Gemini API request failed or returned an empty response."
    return status


def generate_answer(query: str, products: list[ProductOut]) -> str:
    """Generate a grounded natural-language recommendation answer."""
    if not products:
        return _fallback_answer(query, products)

    context = _build_product_context(products)

    user_prompt = (
        f"System instruction: {_SYSTEM_PROMPT}\n\n"
        "User query:\n"
        f"{query}\n\n"
        "Retrieved products (JSON lines):\n"
        f"{context}\n\n"
        "Task:\n"
        "1) Pick the best product from the list and explain why in 3-5 sentences.\n"
        "2) Mention up to 2 alternatives with short trade-offs.\n"
        "3) Do not mention any product that is not in the list.\n"
        "4) Keep response under 140 words."
    )

    text = _call_gemini(user_prompt)
    return text if text else _fallback_answer(query, products)
