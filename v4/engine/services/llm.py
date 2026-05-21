"""DeepSeek LLM client for findings synthesis (OpenAI-compatible HTTP API)."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from openai import OpenAI
from pydantic import ValidationError

from config.settings import settings
from models.conclusion import LlmSynthesisResult

logger = logging.getLogger(__name__)

_MAX_RETRIES = 1


def is_llm_available() -> bool:
    """True when LLM synthesis is enabled and DeepSeek credentials are configured."""
    return bool(settings.use_llm and settings.deepseek_api_key.strip())


def complete_synthesis(
    system_prompt: str,
    user_prompt: str,
) -> Optional[LlmSynthesisResult]:
    """
    Call DeepSeek with JSON output and validate against LlmSynthesisResult.

    Retries once on invalid JSON or schema validation failure.
    Returns None when LLM is unavailable or all attempts fail.
    """
    if not is_llm_available():
        logger.info(
            "LLM synthesis skipped (use_llm=%s, key configured=%s)",
            settings.use_llm,
            bool(settings.deepseek_api_key),
        )
        return None

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url or None,
    )

    last_error: Optional[str] = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            raw = (response.choices[0].message.content or "").strip()
            if not raw:
                last_error = "empty response"
                continue

            payload = _parse_json_payload(raw)
            result = LlmSynthesisResult.model_validate(payload)
            logger.info(
                "LLM synthesis succeeded attempt=%s summary_len=%s",
                attempt + 1,
                len(result.business_summary),
            )
            return result
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "LLM synthesis parse failed attempt=%s/%s: %s",
                attempt + 1,
                _MAX_RETRIES + 1,
                exc,
            )
        except Exception:
            logger.error("DeepSeek API call failed", exc_info=True)
            return None

    if last_error:
        logger.error("LLM synthesis exhausted retries: %s", last_error)
    return None


def _parse_json_payload(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("LLM output must be a JSON object")
    return data
