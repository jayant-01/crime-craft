"""LLM providers.

Three implementations:
  - StubLLM: deterministic templated reply that quotes the first retrieved
    chunk and cites its case_id. Lets us test the orchestrator + citation
    extraction without an API key.
  - AnthropicLLM: Claude Sonnet 4.6 via the official SDK, with prompt
    caching on the system block and adaptive thinking.
  - OpenRouterLLM: any model on OpenRouter's OpenAI-compatible API (including
    the free `:free` tiers). Uses httpx directly — no extra dependency.

All return a plain string. Citation extraction is the orchestrator's job.
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


class OpenRouterLLM:
    """Any OpenRouter model via its OpenAI-compatible chat-completions API.

    OpenRouter exposes many models — including free tiers whose ids end in
    `:free` (e.g. `meta-llama/llama-3.3-70b-instruct:free`). Set
    LLM_PROVIDER=openrouter, LLM_API_KEY=<your key>, and optionally
    LLM_MODEL_ID=<any openrouter model id>. We call the REST endpoint with
    httpx (already a runtime dependency) so no vendor SDK is needed.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    # Used when LLM_MODEL_ID is unset or still points at a Claude id.
    DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
    MAX_TOKENS = 1024
    TIMEOUT_S = 60.0

    @property
    def model_id(self) -> str:
        m = (_settings.llm_model_id or "").strip()
        # The settings default is a Claude id; fall back to a free model unless
        # the operator has pointed LLM_MODEL_ID at a real OpenRouter model.
        if not m or m.startswith("claude"):
            return self.DEFAULT_MODEL
        return m

    def chat(self, system: str, user: str) -> str:
        import httpx

        if not _settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY (OpenRouter) not configured")

        headers = {
            "Authorization": f"Bearer {_settings.llm_api_key}",
            "Content-Type": "application/json",
            # Optional attribution headers OpenRouter uses for its rankings.
            "HTTP-Referer": "https://crime-craft.local",
            "X-Title": _settings.app_name,
        }
        payload = {
            "model": self.model_id,
            "max_tokens": self.MAX_TOKENS,
            "temperature": 0.2,  # grounded Q&A — keep it factual, low variance
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        resp = httpx.post(self.API_URL, headers=headers, json=payload, timeout=self.TIMEOUT_S)
        if resp.status_code != 200:
            # OpenRouter returns a JSON error body; surface it for debugging.
            raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        if data.get("usage"):
            u = data["usage"]
            log.info(
                "openrouter model=%s prompt=%s completion=%s total=%s",
                self.model_id,
                u.get("prompt_tokens"),
                u.get("completion_tokens"),
                u.get("total_tokens"),
            )
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"OpenRouter: unexpected response shape: {data}") from exc


_provider: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _provider
    if _provider is None:
        provider = (_settings.llm_provider or "").lower()
        if provider == "openrouter" and _settings.llm_api_key:
            # OpenRouter can generate real answers over the offline demo
            # retrieval — no need for the full RAG_PROVIDER=live stack.
            _provider = OpenRouterLLM()
        elif provider == "anthropic" and _settings.rag_provider == "live":
            _provider = AnthropicLLM()
        else:
            _provider = StubLLM()
    return _provider


def reset_for_tests() -> None:
    global _provider
    _provider = None
