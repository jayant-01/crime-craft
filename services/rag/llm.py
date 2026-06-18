"""LLM providers.

Two implementations:
  - StubLLM: deterministic templated reply that quotes the first retrieved
    chunk and cites its case_id. Lets us test the orchestrator + citation
    extraction without an API key.
  - AnthropicLLM: Claude Sonnet 4.6 via the official SDK, with prompt
    caching on the system block and adaptive thinking.

Both return a plain string. Citation extraction is the orchestrator's job.
"""

from __future__ import annotations

import logging
from typing import Protocol

from config import get_settings

log = logging.getLogger("rag.llm")
_settings = get_settings()


class LLMProvider(Protocol):
    @property
    def model_id(self) -> str: ...
    def chat(self, system: str, user: str) -> str: ...


class StubLLM:
    """Deterministic stub. Echoes the first retrieved case_id back so citation
    extraction has something to find."""

    MODEL_ID = "stub-llm"

    @property
    def model_id(self) -> str:
        return self.MODEL_ID

    def chat(self, system: str, user: str) -> str:
        # Pull the first [CASE-ID] from the user message if present.
        import re

        m = re.search(r"\[([A-Z]+-\d{4}-\d+)\]", user)
        cite = m.group(1) if m else "FIR-UNKNOWN"
        return (
            "Based on the retrieved cases, here is a brief answer "
            f"grounded in [{cite}]. (This is a stub response — set RAG_PROVIDER=live "
            "and configure ANTHROPIC_API_KEY for real generation.)"
        )


class AnthropicLLM:
    """Claude Sonnet 4.6 via the anthropic SDK.

    Apply prompt caching to the system block — the system prompt is stable
    per role, so repeat queries from the same role pay 10% of input cost on
    the cached prefix. The user message (retrieved chunks + query) varies
    per request and is intentionally outside the cache window.
    """

    MODEL_ID = "claude-sonnet-4-6"
    MAX_TOKENS = 1024

    def __init__(self) -> None:
        self._client = None  # lazy

    @property
    def model_id(self) -> str:
        return self.MODEL_ID

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        import anthropic

        if not _settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY (Anthropic) not configured")
        self._client = anthropic.Anthropic(api_key=_settings.llm_api_key)
        return self._client

    def chat(self, system: str, user: str) -> str:
        client = self._ensure_client()
        response = client.messages.create(
            model=self.MODEL_ID,
            max_tokens=self.MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},  # grounded Q&A doesn't need deep reasoning
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},  # cache the role-specific system prompt
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        # Log cache stats so we can verify prompt caching is working in prod.
        if hasattr(response, "usage"):
            log.info(
                "anthropic usage input=%s cache_read=%s cache_create=%s output=%s",
                getattr(response.usage, "input_tokens", None),
                getattr(response.usage, "cache_read_input_tokens", None),
                getattr(response.usage, "cache_creation_input_tokens", None),
                getattr(response.usage, "output_tokens", None),
            )
        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text
        return ""


_provider: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = AnthropicLLM() if _settings.rag_provider == "live" else StubLLM()
    return _provider


def reset_for_tests() -> None:
    global _provider
    _provider = None
