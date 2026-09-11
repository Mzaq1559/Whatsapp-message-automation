import pytest
from whatsapp_automation.core.templates import (
    extract_variables,
    get_required_custom_variables,
    render_template,
)

def test_extract_variables():
    body = "Hello {name}, your deadline is {deadline}. Sent on {today}."
    vars_found = extract_variables(body)
    assert vars_found == ["name", "deadline", "today"]

def test_get_required_custom_variables():
    body = "Hi {recipient_name}! Room is {room}, date is {today}."
    req = get_required_custom_variables(body)
    assert req == ["room"]

def test_render_template_success():
    body = "Hi {recipient_name}! Meeting in room {room} on {today}."
    rendered = render_template(
        template_body=body,
        recipient_vars={"room": "301B"},
        contact=None,
    )
    assert "room 301B" in rendered
    assert "{today}" not in rendered

def test_render_template_missing_variable_raises():
    body = "Hello {name}, your code is {code}."
    with pytest.raises(ValueError) as exc:
        render_template(template_body=body, recipient_vars={}, contact=None)
    assert "Missing required template variables" in str(exc.value)
