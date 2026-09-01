"""The generic runtime executes the declarative spec: order, validation, follow-ups."""

from form_assistant.masking import PIIRegistry
from form_assistant.orchestrator import FormSession, load_spec


def _session() -> FormSession:
    return FormSession(load_spec(), PIIRegistry())


def test_fields_are_asked_in_spec_order():
    session = _session()
    seen = []
    for answer in ["Alex Sample", "AB123456", "1990-04-12", "12 Sample Street", "no"]:
        seen.append(session.current_field()["id"])
        assert session.submit(answer).accepted
    assert seen == ["full_name", "national_id", "birth_date", "address", "moving_with_family"]
    assert session.is_complete


def test_invalid_value_is_rejected_and_field_stays_current():
    session = _session()
    session.submit("Alex Sample")
    result = session.submit("not-a-document-number")
    assert not result.accepted
    assert "two uppercase letters" in result.error
    assert session.current_field()["id"] == "national_id"
    assert session.submit("AB123456").accepted


def test_conditional_follow_up_is_inserted_only_when_triggered():
    session = _session()
    for answer in ["Alex Sample", "AB123456", "1990-04-12", "12 Sample Street"]:
        session.submit(answer)
    assert session.submit("yes").accepted
    assert session.current_field()["id"] == "family_members"
    assert not session.submit("two").accepted  # follow-up fields validate too
    assert session.submit("2").accepted
    assert session.is_complete


def test_sensitive_answers_are_tokenized_in_masked_view_only():
    session = _session()
    for answer in ["Alex Sample", "AB123456", "1990-04-12", "12 Sample Street", "no"]:
        session.submit(answer)
    masked = session.masked_answers()
    assert masked["full_name"] == "[NAME_1]"
    assert masked["national_id"] == "[ID_1]"
    assert masked["moving_with_family"] == "no"  # non-sensitive stays readable
    assert session.raw_answers()["full_name"] == "Alex Sample"
