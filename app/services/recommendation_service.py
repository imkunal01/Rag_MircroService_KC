"""
Recommendation service.

Phase 4: hybrid retrieval (structured + semantic + lexical intent).

Pipeline:
1. Parse natural language query into structured constraints.
2. Filter catalogue with existing product service helpers.
3. Rank remaining products with weighted hybrid scoring.
"""

from __future__ import annotations

import logging
import re

from app.models.schema import ParsedFiltersOut, ProductOut
from app.rag.embeddings import EmbeddingService
from app.rag.generator import generate_answer
from app.rag.query_parser import parse_query
from app.rag.vector_store import ProductVectorStore
from app.services import product_service


_INTENT_TERMS = {
	"camera": {"camera", "webcam", "photo", "video", "lens", "4k"},
	"gaming": {"gaming", "game", "rgb", "performance", "mechanical"},
	"battery": {"battery", "charging", "charger", "rechargeable", "power"},
	"phone": {"phone", "phones", "mobile", "smartphone", "wireless"},
}

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> set[str]:
	return set(re.findall(r"[a-z0-9]+", text.lower()))


def _normalize_scores(raw_scores: dict[str, float]) -> dict[str, float]:
	if not raw_scores:
		return {}
	values = list(raw_scores.values())
	lo = min(values)
	hi = max(values)
	if hi - lo < 1e-9:
		return {item_id: 1.0 for item_id in raw_scores}
	return {item_id: (score - lo) / (hi - lo) for item_id, score in raw_scores.items()}


def _lexical_overlap_score(query_tokens: set[str], candidate_tokens: set[str]) -> float:
	if not query_tokens or not candidate_tokens:
		return 0.0
	overlap = query_tokens & candidate_tokens
	return len(overlap) / len(query_tokens)


def _intent_match_score(query_tokens: set[str], candidate_tokens: set[str]) -> float:
	query_intents = [
		intent_name
		for intent_name, terms in _INTENT_TERMS.items()
		if query_tokens & terms
	]
	if not query_intents:
		return 0.0

	matched = 0
	for intent_name in query_intents:
		if candidate_tokens & _INTENT_TERMS[intent_name]:
			matched += 1
	return matched / len(query_intents)


def _product_to_semantic_text(product: ProductOut) -> str:
	"""Build rich text used for embeddings and lexical signals."""
	tags = " ".join(product.tags)
	return f"{product.name}. Category: {product.category}. {product.description}. Tags: {tags}"


def _build_why_lines(query: str, products: list[ProductOut]) -> list[str]:
	if not products:
		return ["No products satisfied the current query constraints."]

	query_tokens = _tokenize(query)
	lines: list[str] = []
	for product in products[:3]:
		product_tokens = _tokenize(_product_to_semantic_text(product))
		overlap = sorted(query_tokens & product_tokens)
		reason_bits = [
			f"rating {product.rating:.1f}/5",
			f"price {product.price:.2f}",
		]
		if overlap:
			reason_bits.append("matches: " + ", ".join(overlap[:4]))
		lines.append(f"{product.name}: " + "; ".join(reason_bits))
	return lines


def _build_comparison_lines(products: list[ProductOut]) -> list[str]:
	rows: list[str] = []
	for product in products[:3]:
		tags = ", ".join(product.tags[:3]) if product.tags else "-"
		rows.append(
			f"{product.name} | price {product.price:.2f} | rating {product.rating:.1f}/5 | "
			f"stock {product.stock} | tags {tags}"
		)
	return rows


def recommend_products(query: str, *, limit: int = 10) -> tuple[ParsedFiltersOut, int, list[ProductOut]]:
	"""Return products ranked by hybrid score after structured filtering."""
	known_categories = product_service.get_categories()
	parsed = parse_query(query, known_categories)

	# Structured filter narrows candidate pool before semantic ranking.
	total, filtered_products = product_service.list_products(
		category=parsed.category,
		min_price=parsed.min_price,
		max_price=parsed.max_price,
		limit=10000,
	)

	parsed_filters = ParsedFiltersOut(
		category=parsed.category,
		min_price=parsed.min_price,
		max_price=parsed.max_price,
	)

	if total == 0:
		return parsed_filters, 0, []

	embedder = EmbeddingService()
	candidate_texts = [_product_to_semantic_text(product) for product in filtered_products]
	candidate_ids = [product.id for product in filtered_products]
	candidate_embeddings = embedder.embed_texts(candidate_texts)

	store = ProductVectorStore(dim=embedder.dimension)
	store.add(candidate_ids, candidate_embeddings)

	query_embedding = embedder.embed_query(query)
	hits = store.search(query_embedding, k=len(filtered_products))
	product_by_id = {product.id: product for product in filtered_products}

	semantic_raw = {hit.item_id: hit.score for hit in hits}
	semantic_scores = _normalize_scores(semantic_raw)
	query_tokens = _tokenize(query)

	hybrid_scored: list[tuple[float, ProductOut]] = []
	for product in filtered_products:
		item_id = product.id
		text_tokens = _tokenize(_product_to_semantic_text(product))

		semantic_score = semantic_scores.get(item_id, 0.0)
		lexical_score = _lexical_overlap_score(query_tokens, text_tokens)
		intent_score = _intent_match_score(query_tokens, text_tokens)
		rating_score = max(0.0, min(product.rating / 5.0, 1.0))

		# Weighted rank fusion for hybrid retrieval.
		hybrid_score = (
			0.60 * semantic_score
			+ 0.20 * lexical_score
			+ 0.15 * intent_score
			+ 0.05 * rating_score
		)
		hybrid_scored.append((hybrid_score, product))

	hybrid_scored.sort(key=lambda x: (x[0], x[1].rating, -x[1].price), reverse=True)
	ranked_products = [product for _, product in hybrid_scored[:limit]]

	return parsed_filters, total, ranked_products


def build_recommendation_response(query: str, *, limit: int = 10) -> dict:
	"""End-to-end recommendation payload with answer and explainability."""
	try:
		parsed_filters, total, products = recommend_products(query, limit=limit)
		answer = generate_answer(query, products[:3])
		why_recommended = _build_why_lines(query, products)
		comparison = _build_comparison_lines(products)

		return {
			"query": query,
			"parsed_filters": parsed_filters,
			"answer": answer,
			"total": total,
			"count": len(products),
			"top_products": products[:3],
			"why_recommended": why_recommended,
			"comparison": comparison,
			"products": products,
		}
	except Exception as exc:
		logger.exception("Failed to build recommendation response", extra={"query": query})
		fallback_answer = (
			"I could not generate a complete recommendation right now. "
			"Please try again with a slightly different query."
		)
		return {
			"query": query,
			"parsed_filters": ParsedFiltersOut(),
			"answer": fallback_answer,
			"total": 0,
			"count": 0,
			"top_products": [],
			"why_recommended": ["Recommendation pipeline error handled safely."],
			"comparison": [],
			"products": [],
		}
