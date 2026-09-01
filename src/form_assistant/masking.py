"""PII masking boundary.

Sensitive field values are registered here and replaced by typed placeholder
tokens (e.g. ``[NAME_1]``) before any model-bound payload is built. This is a
structural guarantee: the dialogue runtime never hands raw sensitive values to
the prompt builder, and every outbound payload passes through
:func:`PIIRegistry.audit_payload`, which raises if a registered value leaks.
"""

from __future__ import annotations

import json


class MaskingViolationError(Exception):
    """Raised when a registered sensitive value appears in a model-bound payload."""


class PIIRegistry:
    """Maps raw sensitive values to typed placeholder tokens."""

    def __init__(self) -> None:
        self._token_by_value: dict[str, str] = {}
        self._counters: dict[str, int] = {}

    def register(self, category: str, value: str) -> str:
        """Register a sensitive value and return its placeholder token."""
        value = value.strip()
        if not value:
            raise ValueError("cannot register an empty sensitive value")
        if value in self._token_by_value:
            return self._token_by_value[value]
        self._counters[category] = self._counters.get(category, 0) + 1
        token = f"[{category.upper()}_{self._counters[category]}]"
        self._token_by_value[value] = token
        return token

    def mask_text(self, text: str) -> str:
        """Replace every registered raw value occurring in ``text`` with its token."""
        # Longest values first, so substrings of longer values cannot survive.
        for value in sorted(self._token_by_value, key=len, reverse=True):
            text = text.replace(value, self._token_by_value[value])
        return text

    def audit_payload(self, payload: dict) -> None:
        """Raise :class:`MaskingViolationError` if any registered value is in ``payload``.

        This is the last line of defense before a payload leaves for a model
        provider. It is called on every model call, unconditionally.
        """
        serialized = json.dumps(payload, ensure_ascii=False).lower()
        for value in self._token_by_value:
            if value.lower() in serialized:
                raise MaskingViolationError(
                    f"sensitive value registered as {self._token_by_value[value]!r} "
                    "appears in a model-bound payload"
                )
