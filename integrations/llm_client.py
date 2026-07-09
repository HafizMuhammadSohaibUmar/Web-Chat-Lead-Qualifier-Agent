"""LiteLLM client with Gemini primary and Mistral fallback."""
import asyncio
import os
from typing import Any

import litellm

from config import get_settings

litellm.suppress_debug_info = True


async def complete_chat(messages: list[dict[str, str]], *, max_tokens: int = 350) -> str:
    settings = get_settings()
    if settings.gemini_api_key:
        os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
    if settings.mistral_api_key:
        os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key
    last_error: Exception | None = None
    for model in (settings.primary_model, settings.fallback_model):
        try:
            response: Any = await asyncio.wait_for(
                litellm.acompletion(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.2,
                    timeout=settings.llm_timeout_seconds,
                ),
                timeout=settings.llm_timeout_seconds + 1,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.25)
    raise RuntimeError(f"LLM failed: {last_error}")
