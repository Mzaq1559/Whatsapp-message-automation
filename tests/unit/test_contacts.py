import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from whatsapp_automation.data.models import Base
from whatsapp_automation.core.contacts import (
    create_contact,
    get_contact,
    list_contacts,
    soft_delete_contact,
    bulk_import_csv,
    detect_duplicate,
)

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_and_get_contact(db_session):
    contact = create_contact(
        db_session,
        display_name="Alice Smith",
        whatsapp_ref="+1234567890",
        tags=["work", "vip"],
        notes="Key stakeholder",
    )
    assert contact.id is not None
    assert contact.display_name == "Alice Smith"
    assert contact.tags == ["work", "vip"]

    fetched = get_contact(db_session, contact.id)
    assert fetched is not None
    assert fetched.whatsapp_ref == "+1234567890"

def test_soft_delete_and_list_filtering(db_session):
    c1 = create_contact(db_session, display_name="Bob", whatsapp_ref="+111111", tags=["family"])
    c2 = create_contact(db_session, display_name="Charlie", whatsapp_ref="+222222", tags=["work"])

    active_contacts = list_contacts(db_session)
    assert len(active_contacts) == 2

    soft_delete_contact(db_session, c1.id)

    active_after = list_contacts(db_session)
    assert len(active_after) == 1
    assert active_after[0].display_name == "Charlie"

    family_contacts = list_contacts(db_session, tag="family")
    assert len(family_contacts) == 0  # archived c1 had tag family

def test_detect_duplicate(db_session):
    create_contact(db_session, display_name="Dave", whatsapp_ref="+999888")
    dup = detect_duplicate(db_session, display_name="Dave", whatsapp_ref="+999888")
    assert dup is not None

    no_dup = detect_duplicate(db_session, display_name="Eve", whatsapp_ref="+000000")
    assert no_dup is None

def test_bulk_import_csv(db_session):
    csv_data = "Name,Phone,Tags\nUser One,+111,test\nUser Two,+222,test\nUser One,+111,dup\n"
    res = bulk_import_csv(
        db_session,
        csv_text_or_path=csv_data,
        column_mapping={"display_name": "Name", "whatsapp_ref": "Phone", "tags": "Tags"},
        skip_duplicates=True,
    )
    assert res["imported_count"] == 2
    assert res["skipped_duplicates_count"] == 1
