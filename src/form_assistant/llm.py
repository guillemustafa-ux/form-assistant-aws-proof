"""Model provider interface.

Two implementations only:

- :class:`MockProvider` — deterministic, offline, records every payload it is
  handed so tests can prove what actually left the application boundary.
- :class:`AnthropicProvider` — real calls via the ``anthropic`` SDK, used only
  when ``ANTHROPIC_API_KEY`` is set.

A payload is always ``{"system": str, "messages": [{"role": str, "content": str}]}``.
"""

from __future__ import annotations

import os
from typing import Protocol


class LLMProvider(Protocol):
    def complete(self, payload: dict) -> str: ...


class MockProvider:
    """Deterministic offline provider. Captures every outbound payload."""

    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def complete(self, payload: dict) -> str:
        self.payloads.append(payload)
        return "(mock model) Answer grounded strictly in the cited passage above."


class AnthropicProvider:
    """Claude provider. Instantiated only when an API key is configured."""

    MODEL = "claude-sonnet-5"

    def __init__(self, api_key: str) -> None:
        import anthropic  # imported lazily; not needed for offline use

        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, payload: dict) -> str:
        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            system=payload["system"],
            messages=payload["messages"],
        )
        return "".join(block.text for block in response.content if block.type == "text")


def build_provider() -> LLMProvider:
    """Return the Anthropic provider if a key is configured, else the mock."""
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").replace('"', "").strip()
    if api_key:
        return AnthropicProvider(api_key)
    return MockProvider()
