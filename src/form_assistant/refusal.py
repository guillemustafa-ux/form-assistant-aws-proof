"""Refusal logic for questions that require a legal assessment.

The triggers are declarative data, not code: adding a new refusal category is
an edit to ``TRIGGERS``, not to the runtime.
"""

from __future__ import annotations

TRIGGERS: list[dict] = [
    {
        "id": "legal-assessment",
        "phrases": ["appeal", "sue", "lawsuit", "legal advice", "lawyer", "court", "attorney"],
        "reason": "The question asks for a legal assessment of an individual case.",
    },
    {
        "id": "eligibility-ruling",
        "phrases": ["am i entitled", "do i qualify", "is it legal for me"],
        "reason": "The question asks for a binding eligibility ruling.",
    },
]

REFUSAL_MESSAGE = (
    "I cannot answer this question. It requires a legal assessment, which this "
    "assistant is not allowed to provide. Please contact a qualified advisor or "
    "the responsible authority."
)


def check_refusal(question: str) -> dict | None:
    """Return the matching trigger (with reason) if the question must be refused."""
    lowered = question.lower()
    for trigger in TRIGGERS:
        for phrase in trigger["phrases"]:
            if phrase in lowered:
                return {"trigger_id": trigger["id"], "phrase": phrase, "reason": trigger["reason"]}
    return None
