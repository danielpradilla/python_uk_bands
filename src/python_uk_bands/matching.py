"""Entity matching helpers."""

from __future__ import annotations

import re
import unicodedata


def normalize_name(value: str | None) -> str:
    """Normalize an entity name for simple fuzzy comparisons."""
    if not value:
        return ""
    ascii_value = unicodedata.normalize("NFKD", value).encode(
        "ascii",
        "ignore",
    ).decode("ascii")
    ascii_value = re.sub(r"\s*(?:&|\+)\s*", " and ", ascii_value)
    ascii_value = re.sub(r"^\s*the\b\s*", "", ascii_value, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower())


def infer_match_confidence(target_name: str, candidate_name: str, *, is_first_result: bool) -> str:
    """Assign a simple match confidence label for a candidate name."""
    target = normalize_name(target_name)
    candidate = normalize_name(candidate_name)
    if not target or not candidate:
        return "none"
    if target == candidate:
        return "exact"
    if candidate in target or target in candidate:
        return "approximate"
    if is_first_result:
        return "fallback"
    return "low"
