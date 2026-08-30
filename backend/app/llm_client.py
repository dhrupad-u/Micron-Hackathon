from __future__ import annotations

import json
import logging
import os
import time
from typing import Callable, Type, TypeVar

from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _build_mock_response(response_model: Type[T], fallback: Callable[[], T]) -> T:
    try:
        return fallback()
    except Exception:
        return response_model.model_construct()


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def call_structured_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    response_model: Type[T],
    fallback: Callable[[], T],
    api_key: str | None = None,
    model: str | None = None,
    timeout_seconds: int = 45,
    max_attempts: int = 2,
) -> T:
    """Structured LLM wrapper with multi-provider retry + safe fallback.

    Provider priority:
      1. Groq (any key starting with gsk_) — very generous free tier, fast
      2. Gemini (GEMINI_API_KEY)
      3. xAI (XAI_API_KEY, if not a Groq key)
      4. OpenAI (OPENAI_API_KEY)

    Checks ALL env vars for Groq keys (gsk_ prefix) regardless of env var name.
    Falls back to static stub if all providers fail.
    """
    _load_env()

    raw_xai    = (os.getenv("XAI_API_KEY")    or "").strip()
    raw_gemini = (os.getenv("GEMINI_API_KEY") or "").strip()
    raw_openai = (os.getenv("OPENAI_API_KEY") or "").strip()
    raw_groq   = (os.getenv("GROQ_API_KEY")   or "").strip()

    # Any key starting with gsk_ is a Groq key, regardless of which env var holds it
    groq_candidates = [k for k in [raw_xai, raw_groq] if k.startswith("gsk_")]
    groq_key   = groq_candidates[0] if groq_candidates else ""
    gemini_key = raw_gemini if not raw_gemini.startswith("gsk_") else ""
    xai_key    = raw_xai if raw_xai and not raw_xai.startswith("gsk_") else ""
    openai_key = raw_openai

    # Build ordered provider list: Groq first (most generous free tier)
    providers: list[dict] = []

    if groq_key:
        providers.append({
            "key": groq_key,
            "url": "https://api.groq.com/openai/v1",
            "model": "openai/gpt-oss-120b",
            "name": "Groq/gpt-oss-120b",
        })

    if gemini_key:
        providers.append({
            "key": gemini_key,
            "url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "model": model or "gemini-2.5-flash",
            "name": "Gemini/gemini-2.5-flash",
        })

    if xai_key:
        providers.append({
            "key": xai_key,
            "url": "https://api.x.ai/v1",
            "model": "grok-4",
            "name": "xAI/grok-4",
        })

    if openai_key:
        providers.append({
            "key": openai_key,
            "url": None,
            "model": model or "gpt-4o-mini",
            "name": "OpenAI/gpt-4o-mini",
        })

    if not providers:
        LOGGER.warning("No LLM API key configured; using fallback for %s", response_model.__name__)
        return fallback()

    schema = response_model.model_json_schema()
    system_msg = (
        f"{system_prompt}\n\n"
        f"Respond ONLY with a valid JSON object matching this schema (no markdown, no code fences):\n"
        f"{json.dumps(schema, indent=2)}"
    )

    try:
        import openai as _openai  # type: ignore
    except Exception:
        LOGGER.warning("openai library not installed; using fallback for %s", response_model.__name__)
        return fallback()

    for prov in providers:
        for attempt in range(1, max_attempts + 1):
            try:
                client_kwargs: dict = {"api_key": prov["key"], "timeout": timeout_seconds}
                if prov["url"]:
                    client_kwargs["base_url"] = prov["url"]
                client = _openai.OpenAI(**client_kwargs)
                completion = client.chat.completions.create(
                    model=prov["model"],
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw = completion.choices[0].message.content or ""
                parsed = response_model.model_validate_json(raw)
                LOGGER.info("LLM success via %s for %s", prov["name"], response_model.__name__)
                return parsed
            except Exception as exc:
                LOGGER.warning(
                    "LLM provider %s attempt %s/%s failed for %s: %s",
                    prov["name"], attempt, max_attempts, response_model.__name__, exc,
                )
                time.sleep(0.5 * attempt)

    LOGGER.warning("All LLM providers failed for %s; using deterministic fallback", response_model.__name__)
    fallback_result = fallback()
    try:
        json.loads(json.dumps(fallback_result.model_dump()))
        return fallback_result
    except Exception:
        return _build_mock_response(response_model, fallback)
