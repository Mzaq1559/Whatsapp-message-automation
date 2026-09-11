import csv
import io
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..data.models import Contact


def utc_now() -> datetime:
    return datetime.now(UTC)

def normalize_whatsapp_ref(ref: str) -> str:
    """Normalize phone numbers or search terms by stripping whitespace/dashes if numeric."""
    cleaned = ref.strip()
    # If it's a numeric phone number string, keep digits and leading '+'
    if any(char.isdigit() for char in cleaned) and not any(char.isalpha() for char in cleaned):
        numeric_parts = "".join(c for c in cleaned if c.isdigit() or c == "+")
        return numeric_parts
    return cleaned

def create_contact(
    db: Session,
    display_name: str,
    whatsapp_ref: str,
    is_group: bool = False,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> Contact:
    norm_ref = normalize_whatsapp_ref(whatsapp_ref)
    contact = Contact(
        display_name=display_name.strip(),
        whatsapp_ref=norm_ref,
        is_group=is_group,
        notes=notes.strip() if notes else None,
    )
    if tags:
        contact.tags = [t.strip().lower() for t in tags if t.strip()]
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

def get_contact(db: Session, contact_id: int) -> Contact | None:
    return db.query(Contact).filter(Contact.id == contact_id).first()

def update_contact(
    db: Session,
    contact_id: int,
    display_name: str | None = None,
    whatsapp_ref: str | None = None,
    is_group: bool | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> Contact | None:
    contact = get_contact(db, contact_id)
    if not contact:
        return None

    if display_name is not None:
        contact.display_name = display_name.strip()
    if whatsapp_ref is not None:
        contact.whatsapp_ref = normalize_whatsapp_ref(whatsapp_ref)
    if is_group is not None:
        contact.is_group = is_group
    if tags is not None:
        contact.tags = [t.strip().lower() for t in tags if t.strip()]
    if notes is not None:
        contact.notes = notes.strip() if notes else None

    contact.updated_at = utc_now()
    db.commit()
    db.refresh(contact)
    return contact

def soft_delete_contact(db: Session, contact_id: int) -> bool:
    contact = get_contact(db, contact_id)
    if not contact:
        return False
    contact.archived_at = utc_now()
    db.commit()
    return True

def restore_contact(db: Session, contact_id: int) -> bool:
    contact = get_contact(db, contact_id)
    if not contact:
        return False
    contact.archived_at = None
    db.commit()
    return True

def list_contacts(
    db: Session,
    tag: str | None = None,
    is_group: bool | None = None,
    search: str | None = None,
    include_archived: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[Contact]:
    query = db.query(Contact)
    if not include_archived:
        query = query.filter(Contact.archived_at.is_(None))

    if is_group is not None:
        query = query.filter(Contact.is_group == is_group)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Contact.display_name.ilike(search_term),
                Contact.whatsapp_ref.ilike(search_term),
                Contact.notes.ilike(search_term),
            )
        )

    contacts = query.order_by(Contact.display_name.asc()).offset(offset).limit(limit).all()

    if tag:
        target_tag = tag.strip().lower()
        contacts = [c for c in contacts if target_tag in c.tags]

    return contacts

def detect_duplicate(db: Session, display_name: str, whatsapp_ref: str) -> Contact | None:
    norm_ref = normalize_whatsapp_ref(whatsapp_ref)
    name = display_name.strip()
    return (
        db.query(Contact)
        .filter(
            Contact.archived_at.is_(None),
            or_(
                Contact.whatsapp_ref == norm_ref,
                Contact.display_name.ilike(name),
            ),
        )
        .first()
    )

def bulk_import_csv(
    db: Session,
    csv_text_or_path: str,
    column_mapping: dict[str, str],  # e.g. {"display_name": "Name", "whatsapp_ref": "Phone", "tags": "Tags"}
    is_group: bool = False,
    skip_duplicates: bool = True,
) -> dict[str, Any]:
    """
    Import contacts from CSV content or file path.
    column_mapping maps target fields ('display_name', 'whatsapp_ref', 'tags', 'notes') to CSV header names.
    """
    if isinstance(csv_text_or_path, str) and ("\n" in csv_text_or_path or csv_text_or_path.startswith("display_name")):
        file_obj = io.StringIO(csv_text_or_path)
    else:
        file_obj = open(csv_text_or_path, "r", encoding="utf-8-sig")

    try:
        reader = csv.DictReader(file_obj)
        name_col = column_mapping.get("display_name", "display_name")
        ref_col = column_mapping.get("whatsapp_ref", "whatsapp_ref")
        tags_col = column_mapping.get("tags", "tags")
        notes_col = column_mapping.get("notes", "notes")

        imported = 0
        skipped = 0
        errors: list[str] = []

        for idx, row in enumerate(reader, start=1):
            disp_name = row.get(name_col, "").strip() if name_col in row else ""
            wa_ref = row.get(ref_col, "").strip() if ref_col in row else ""

            if not disp_name or not wa_ref:
                errors.append(f"Row {idx}: missing required display_name or whatsapp_ref.")
                continue

            if skip_duplicates and detect_duplicate(db, disp_name, wa_ref):
                skipped += 1
                continue

            raw_tags = row.get(tags_col, "") if tags_col in row else ""
            tag_list = [t.strip().lower() for t in raw_tags.split(",") if t.strip()] if raw_tags else []
            notes_val = row.get(notes_col, "") if notes_col in row else None

            create_contact(
                db=db,
                display_name=disp_name,
                whatsapp_ref=wa_ref,
                is_group=is_group,
                tags=tag_list,
                notes=notes_val,
            )
            imported += 1

        return {
            "imported_count": imported,
            "skipped_duplicates_count": skipped,
            "errors": errors,
        }
    finally:
        if hasattr(file_obj, "close") and file_obj != io.StringIO:
            file_obj.close()
