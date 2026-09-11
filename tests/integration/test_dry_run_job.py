import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from whatsapp_automation.data.models import Base, SendLog
from whatsapp_automation.core.contacts import create_contact
from whatsapp_automation.core.templates import create_template
from whatsapp_automation.core.jobs import create_job, execute_dry_run
from whatsapp_automation.core.history import query_send_logs

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_full_dry_run_job_end_to_end(db_session):
    # 1. Create contacts
    c1 = create_contact(db_session, display_name="Alice", whatsapp_ref="+1111111111")
    c2 = create_contact(db_session, display_name="Bob", whatsapp_ref="+2222222222")

    # 2. Create template
    tmpl = create_template(
        db_session,
        name="Study Reminder",
        body="Hello {recipient_name}! Room is {room} for assignment {task}.",
    )

    # 3. Create Job with variables
    job = create_job(
        db_session,
        name="Weekly Nudge",
        template_id=tmpl.id,
        recipient_data=[
            {"contact_id": c1.id, "variables": {"room": "101", "task": "Lab 1"}},
            {"contact_id": c2.id, "variables": {"room": "102", "task": "Lab 2"}},
        ],
        safety_mode="Conservative",
    )

    # 4. Execute Dry-Run
    result = execute_dry_run(db_session, job_id=job.id)

    assert result["status"] == "completed"
    assert result["total_recipients"] == 2
    assert result["sent_count"] == 2
    assert result["failed_count"] == 0

    # 5. Verify SendLogs created
    logs, count = query_send_logs(db_session, job_id=job.id)
    assert count == 2
    assert any("Alice" in l["rendered_text"] and "Lab 1" in l["rendered_text"] for l in logs)
    assert any("Bob" in l["rendered_text"] and "Lab 2" in l["rendered_text"] for l in logs)
