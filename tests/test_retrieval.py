"""Answers carry correct source references; out-of-corpus returns no source."""

from form_assistant.app import FormAssistant
from form_assistant.llm import MockProvider
from form_assistant.retrieval import Corpus


def test_answer_carries_a_traceable_source_reference():
    passage = Corpus.load().search("When is the registration deadline?")
    assert passage is not None
    assert passage.source.doc_id == "sample-residence-registration-guide"
    assert passage.source.section_id == "deadlines"
    assert "14 days" in passage.text


def test_fees_question_hits_the_fees_document():
    passage = Corpus.load().search("Is there a fee for the registration certificate?")
    assert passage is not None
    assert passage.source.doc_id == "sample-fees-processing-guide"


def test_out_of_corpus_question_returns_no_source():
    assert Corpus.load().search("What is the weather like today?") is None


def test_assistant_reports_no_source_and_makes_no_model_call():
    provider = MockProvider()
    assistant = FormAssistant.default(provider=provider)
    result = assistant.ask("What is the weather like today?")
    assert result["type"] == "no_source"
    assert "No source found" in result["message"]
    assert provider.payloads == []


def test_assistant_answer_includes_the_source():
    assistant = FormAssistant.default(provider=MockProvider())
    result = assistant.ask("When is the registration deadline?")
    assert result["type"] == "answer"
    assert result["source"] == {
        "doc_id": "sample-residence-registration-guide",
        "section_id": "deadlines",
        "heading": "Registration deadline",
    }
