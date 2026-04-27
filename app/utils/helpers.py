"""
Shared utility helpers.

Helpers used by retrieval and response formatting.
"""

from __future__ import annotations

import re
from typing import Iterable


def normalize_whitespace(text: str) -> str:
	"""Collapse repeated whitespace and trim leading/trailing spaces."""
	return re.sub(r"\s+", " ", text).strip()


def truncate_text(text: str, max_chars: int) -> str:
	"""Trim text to a maximum character budget with a visible ellipsis."""
	cleaned = normalize_whitespace(text)
	if max_chars <= 0:
		return ""
	if len(cleaned) <= max_chars:
		return cleaned
	if max_chars <= 3:
		return cleaned[:max_chars]
	return cleaned[: max_chars - 3].rstrip() + "..."


def chunk_by_char_budget(items: Iterable[str], max_chars: int) -> list[str]:
	"""Keep appending items until the global character budget is reached."""
	chunks: list[str] = []
	used = 0
	for item in items:
		if max_chars <= 0:
			break
		if used + len(item) > max_chars:
			break
		chunks.append(item)
		used += len(item)
	return chunks
