"""Spec-driven dialogue runtime.

The behavioral specification (field order, validation rules, conditional
follow-ups, which fields are sensitive) is pure JSON data. This runtime is
generic: it executes whatever spec it is given and contains no knowledge of
any particular form. Swapping the spec changes the assistant's behavior
without touching code.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .masking import PIIRegistry

DEFAULT_SPEC_PATH = Path(__file__).parent / "fixtures" / "form_spec.json"


def load_spec(path: Path = DEFAULT_SPEC_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class SubmitResult:
    accepted: bool
    error: str | None = None


class FormSession:
    """Executes one dialogue over a declarative form spec.

    Raw sensitive values are kept in a private store and never exposed to the
    prompt-building path: :meth:`masked_answers` is the only view the model
    side ever sees.
    """

    def __init__(self, spec: dict, registry: PIIRegistry) -> None:
        self._registry = registry
        self._queue: list[dict] = [dict(field) for field in spec["fields"]]
        self._raw: dict[str, str] = {}
        self._masked: dict[str, str] = {}

    def current_field(self) -> dict | None:
        return self._queue[0] if self._queue else None

    @property
    def is_complete(self) -> bool:
        return not self._queue

    def submit(self, value: str) -> SubmitResult:
        field = self.current_field()
        if field is None:
            return SubmitResult(accepted=False, error="form is already complete")
        value = value.strip()

        pattern = field.get("validation", {}).get("pattern")
        if pattern and not re.fullmatch(pattern, value):
            return SubmitResult(
                accepted=False,
                error=field.get("validation", {}).get("message", f"invalid value for {field['id']}"),
            )

        self._raw[field["id"]] = value
        if field.get("sensitive"):
            self._masked[field["id"]] = self._registry.register(field["sensitive"], value)
        else:
            self._masked[field["id"]] = value

        self._queue.pop(0)
        follow_up = field.get("follow_up")
        if follow_up and value == follow_up["if_equals"]:
            self._queue[0:0] = [dict(f) for f in follow_up["fields"]]
        return SubmitResult(accepted=True)

    def masked_answers(self) -> dict[str, str]:
        """Answers with sensitive values replaced by tokens. Safe for model payloads."""
        return dict(self._masked)

    def raw_answers(self) -> dict[str, str]:
        """Raw answers for the form-submission channel ONLY. Never for model payloads."""
        return dict(self._raw)
