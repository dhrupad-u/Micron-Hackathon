"""Hero illustration generation via Pollinations.ai (free, no API key required).

Generates one flat-illustration hero image per concept and caches it under
backend/generated_images/. Any network failure returns None — the frontend
falls back to a CSS gradient hero.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

LOGGER = logging.getLogger(__name__)

_IMAGES_DIR = Path(__file__).resolve().parent.parent / "generated_images"


def _safe_slug(text: str, max_len: int = 120) -> str:
    """URL-encode a prompt string for Pollinations."""
    import urllib.parse
    return urllib.parse.quote(text[:max_len], safe="")


def _prompt_for(title: str, definition: str, key_facts: list[str]) -> str:
    facts = "; ".join(key_facts[:3]) if key_facts else ""
    return (
        f"flat vector illustration for an educational app lesson about {title}. "
        f"Visual concept: {definition[:120]}. "
        f"Key elements: {facts}. "
        "Style: modern flat illustration, soft rounded shapes, cheerful vibrant palette "
        "(greens, blues, warm yellow accents), clean white background, no text, no letters, "
        "square composition, polished learning-app hero image."
    )


def hero_image_url(
    concept_id: str,
    title: str,
    definition: str,
    key_facts: list[str] | None = None,
) -> str | None:
    """Return a URL for the concept's hero image, generating + caching on first call."""
    if not concept_id:
        return None

    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Sanitise concept_id to only alphanum + hyphen for filename safety
    safe_id = re.sub(r"[^a-z0-9\-]", "-", concept_id.lower())[:60]
    cache_path = _IMAGES_DIR / f"{safe_id}.png"

    if cache_path.exists() and cache_path.stat().st_size > 1024:
        return f"/static/images/{safe_id}.png"

    prompt = _prompt_for(title, definition, key_facts or [])

    try:
        import httpx

        url = (
            f"https://image.pollinations.ai/prompt/{_safe_slug(prompt)}"
            f"?width=800&height=400&nologo=true&seed=42&model=flux"
        )
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type:
            LOGGER.warning(
                "Pollinations returned non-image content-type '%s' for %s",
                content_type,
                concept_id,
            )
            return None

        cache_path.write_bytes(response.content)
        LOGGER.info("Generated hero image via Pollinations.ai for %s", concept_id)
        return f"/static/images/{safe_id}.png"

    except Exception as exc:  # noqa: BLE001 — hero art is best-effort
        LOGGER.warning("Hero image generation failed for %s: %s", concept_id, exc)
        return None
