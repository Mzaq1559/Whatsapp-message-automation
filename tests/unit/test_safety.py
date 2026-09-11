import pytest
from whatsapp_automation.core.validation import check_max_sends_per_run

def test_check_max_sends_per_run_conservative():
    ok, msg = check_max_sends_per_run(proposed_send_count=20, safety_mode="Conservative")
    assert ok is True

    ok, msg = check_max_sends_per_run(proposed_send_count=30, safety_mode="Conservative")
    assert ok is False
    assert "Run cap exceeded" in msg

def test_check_max_sends_per_run_standard():
    ok, msg = check_max_sends_per_run(proposed_send_count=45, safety_mode="Standard")
    assert ok is True

    ok, msg = check_max_sends_per_run(proposed_send_count=60, safety_mode="Standard")
    assert ok is False
