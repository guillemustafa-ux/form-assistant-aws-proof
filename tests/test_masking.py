"""Core proof: registered sensitive values never reach a model-bound payload."""

import json

import pytest

from form_assistant.app import FormAssistant
from form_assistant.llm import MockProvider
from form_assistant.masking import MaskingViolationError, PIIRegistry

SENSITIVE_ANSWERS = {
    "full_name": "Alex Sample",
    "national_id": "AB123456",
    "birth_date": "1990-04-12",
    "address": "12 Sample Street, Exampleville",
}
DIALOGUE = ["Alex Sample", "AB123456", "1990-04-12", "12 Sample Street, Exampleville", "yes", "2"]


def _run_full_dialogue(assistant: FormAssistant) -> None:
    for answer in DIALOGUE:
        result = assistant.session.submit(answer)
        assert result.accepted, result.error
    assert assistant.session.is_complete


def test_no_sensitive_value_ever_reaches_a_model_payload():
    provider = MockProvider()
    assistant = FormAssistant.default(provider=provider)
    _run_full_dialogue(assistant)

    # Ask a grounded question, plus one that embeds PII in the question itself.
    assert assistant.ask("When is the registration deadline?")["type"] == "answer"
    result = assistant.ask(
        "My document number is AB123456, which documents do I need for the registration?"
    )
    assert result["type"] == "answer"

    assert provider.payloads, "expected at least one model call"
    for payload in provider.payloads:
        serialized = json.dumps(payload)
        for raw in SENSITIVE_ANSWERS.values():
            assert raw not in serialized, f"sensitive value {raw!r} leaked to a model payload"

    # The masked state (typed tokens) did make it into the payload.
    last = json.dumps(provider.payloads[-1])
    assert "[NAME_1]" in last
    assert "[ID_1]" in last


def test_question_text_is_masked_not_dropped():
    provider = MockProvider()
    assistant = FormAssistant.default(provider=provider)
    _run_full_dialogue(assistant)
    assistant.ask("My document number is AB123456, which documents do I need for the registration?")
    content = provider.payloads[-1]["messages"][0]["content"]
    assert "AB123456" not in content
    assert "[ID_1]" in content


def test_audit_catches_a_deliberately_leaked_value():
    registry = PIIRegistry()
    registry.register("name", "Alex Sample")
    leaked = {"system": "x", "messages": [{"role": "user", "content": "user is Alex Sample"}]}
    with pytest.raises(MaskingViolationError):
        registry.audit_payload(leaked)


def test_audit_passes_a_clean_payload():
    registry = PIIRegistry()
    token = registry.register("name", "Alex Sample")
    clean = {"system": "x", "messages": [{"role": "user", "content": f"user is {token}"}]}
    registry.audit_payload(clean)  # must not raise
