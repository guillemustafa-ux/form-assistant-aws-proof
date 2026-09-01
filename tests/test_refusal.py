"""Legal-assessment triggers refuse; normal questions do not."""

from form_assistant.app import FormAssistant
from form_assistant.llm import MockProvider
from form_assistant.refusal import REFUSAL_MESSAGE, check_refusal


def test_legal_assessment_question_is_refused():
    match = check_refusal("Should I appeal the rejection decision?")
    assert match is not None
    assert match["trigger_id"] == "legal-assessment"
    assert match["reason"]


def test_normal_question_is_not_refused():
    assert check_refusal("Which documents do I need for the registration?") is None


def test_refused_question_never_triggers_a_model_call():
    provider = MockProvider()
    assistant = FormAssistant.default(provider=provider)
    result = assistant.ask("Can I sue the office over this decision?")
    assert result["type"] == "refusal"
    assert result["message"] == REFUSAL_MESSAGE
    assert result["reason"]
    assert provider.payloads == []
