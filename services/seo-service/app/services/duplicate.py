"""Duplicate content detection for SEO pages."""
from __future__ import annotations

from difflib import SequenceMatcher

from app.config import settings


def _extract_text(content: dict) -> str:
    """Extract intro + local_intro text from AI-generated content JSON."""
    intro = content.get("intro", "")
    local_intro = content.get("local_intro", "")
    return f"{intro} {local_intro}".strip()


def is_duplicate(new_content: dict, existing_contents: list[dict]) -> bool:
    """
    Check if new_content is too similar to any of the existing contents.
    Only compares intro + local_intro fields, scoped to the same service type.
    Returns True if a duplicate is detected above the threshold.
    """
    threshold = settings.DUPLICATE_THRESHOLD
    new_text = _extract_text(new_content)
    if not new_text:
        return False

    for existing in existing_contents:
        existing_text = _extract_text(existing)
        if not existing_text:
            continue
        ratio = SequenceMatcher(None, new_text, existing_text).ratio()
        if ratio >= threshold:
            return True

    return False
