"""Application wiring: assistant facade and AWS Lambda handler.

Every model call funnels through :meth:`FormAssistant.ask`, which builds the
payload exclusively from masked material and then runs the registry audit.
There is no other code path to a provider.
"""

from __future__ import annotations

import json

from .llm import LLMProvider, build_provider
from .masking import PIIRegistry
from .orchestrator import FormSession, load_spec
from .refusal import REFUSAL_MESSAGE, check_refusal
from .retrieval import Corpus

SYSTEM_PROMPT = (
    "You are a form-filling assistant. Answer ONLY from the cited guidance "
    "passage provided in the user message. If the passage does not answer the "
    "question, say so. Placeholder tokens such as [NAME_1] stand for personal "
    "data you must never ask to reveal."
)

NO_SOURCE_MESSAGE = (
    "No source found. The available guidance does not cover this question, "
    "so I will not guess."
)


class FormAssistant:
    def __init__(self, spec: dict, corpus: Corpus, provider: LLMProvider) -> None:
        self.registry = PIIRegistry()
        self.session = FormSession(spec, self.registry)
        self.corpus = corpus
        self.provider = provider

    @classmethod
    def default(cls, provider: LLMProvider | None = None) -> "FormAssistant":
        return cls(load_spec(), Corpus.load(), provider or build_provider())

    def ask(self, question: str) -> dict:
        """Answer a question: refuse, cite a source, or admit there is none."""
        refusal = check_refusal(question)
        if refusal:
            return {"type": "refusal", "message": REFUSAL_MESSAGE, **refusal}

        passage = self.corpus.search(question)
        if passage is None:
            # No grounding available: no model call is made at all.
            return {"type": "no_source", "message": NO_SOURCE_MESSAGE}

        payload = {
            "system": SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Guidance passage [{passage.source.doc_id} / "
                        f"{passage.source.section_id}]:\n{passage.text}\n\n"
                        f"Form state (masked): "
                        f"{json.dumps(self.session.masked_answers(), ensure_ascii=False)}\n\n"
                        f"Question: {self.registry.mask_text(question)}"
                    ),
                }
            ],
        }
        self.registry.audit_payload(payload)  # raises on any PII leak
        answer = self.provider.complete(payload)
        return {
            "type": "answer",
            "answer": answer,
            "passage": passage.text,
            "source": {
                "doc_id": passage.source.doc_id,
                "section_id": passage.source.section_id,
                "heading": passage.source.heading,
            },
        }


def lambda_handler(event: dict, context: object) -> dict:
    """API Gateway (proxy) entry point.

    Request body: ``{"question": str, "fields": {field_id: value, ...}}``.
    ``fields`` values whose spec entry is sensitive are registered in the
    masking registry before the question is answered.
    """
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "request body must be JSON"})

    question = body.get("question")
    if not question:
        return _response(400, {"error": "'question' is required"})

    assistant = FormAssistant.default()
    spec_fields = {f["id"]: f for f in load_spec()["fields"]}
    for field_id, value in (body.get("fields") or {}).items():
        field = spec_fields.get(field_id)
        if field and field.get("sensitive") and str(value).strip():
            assistant.registry.register(field["sensitive"], str(value))

    return _response(200, assistant.ask(question))


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
