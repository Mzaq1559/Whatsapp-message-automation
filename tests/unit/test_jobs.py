import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from whatsapp_automation.data.models import Base
from whatsapp_automation.core.contacts import create_contact
from whatsapp_automation.core.templates import create_template
from whatsapp_automation.core.jobs import (
    create_job,
    clone_job,
    validate_job,
    retry_failed_recipients,
)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_job_creation_and_cloning(db_session):
    c1 = create_contact(db_session, display_name="User 1", whatsapp_ref="+100")
    t1 = create_template(db_session, name="Nudge", body="Hello {recipient_name}")

    job = create_job(
        db_session,
        name="Test Campaign",
        template_id=t1.id,
        recipient_data=[{"contact_id": c1.id, "variables": {}}],
    )

    assert job.status == "draft"
    assert len(job.recipients) == 1
    assert job.template_snapshot_body == "Hello {recipient_name}"

    cloned = clone_job(db_session, job.id)
    assert cloned.id != job.id
    assert cloned.name == "Copy of Test Campaign"
    assert len(cloned.recipients) == 1

def test_job_validation(db_session):
    c1 = create_contact(db_session, display_name="User 1", whatsapp_ref="+100")
    t1 = create_template(db_session, name="Event", body="Hi {recipient_name}, room is {room}")

    # Job missing required variable 'room'
    job = create_job(
        db_session,
        name="Missing Var Campaign",
        template_id=t1.id,
        recipient_data=[{"contact_id": c1.id, "variables": {}}],
    )

    valid, errors = validate_job(db_session, job.id)
    assert not valid
    assert any("missing variables: room" in e for e in errors)
