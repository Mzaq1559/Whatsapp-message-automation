from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ..data.models import Job, JobRecipient, SendLog
from .templates import get_template, render_template
from .validation import validate_job_for_execution


def utc_now() -> datetime:
    return datetime.now(UTC)

def create_job(
    db: Session,
    name: str,
    template_id: int,
    recipient_data: list[dict[str, Any]],  # [{"contact_id": 1, "variables": {"var": "val"}}]
    safety_mode: str = "Conservative",
) -> Job:
    template = get_template(db, template_id)
    if not template:
        raise ValueError(f"Template ID {template_id} does not exist.")

    job = Job(
        name=name.strip(),
        template_id=template_id,
        template_snapshot_body=template.body,
        status="draft",
        safety_mode=safety_mode,
    )
    db.add(job)
    db.flush()  # get job.id

    for r_item in recipient_data:
        contact_id = r_item["contact_id"]
        vars_dict = r_item.get("variables", {})
        recipient = JobRecipient(
            job_id=job.id,
            contact_id=contact_id,
            status="pending",
        )
        recipient.variables = vars_dict
        db.add(recipient)

    db.commit()
    db.refresh(job)
    return job

def get_job(db: Session, job_id: int) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()

def list_jobs(
    db: Session,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Job]:
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    return query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

def clone_job(db: Session, job_id: int, new_name: str | None = None) -> Job:
    original = get_job(db, job_id)
    if not original:
        raise ValueError(f"Job ID {job_id} not found.")

    recipients_data = [
        {"contact_id": r.contact_id, "variables": r.variables} for r in original.recipients
    ]

    clone_name = new_name or f"Copy of {original.name}"
    return create_job(
        db=db,
        name=clone_name,
        template_id=original.template_id,
        recipient_data=recipients_data,
        safety_mode=original.safety_mode,
    )

def validate_job(db: Session, job_id: int) -> tuple[bool, list[str]]:
    job = get_job(db, job_id)
    if not job:
        return False, ["Job not found."]

    errors = validate_job_for_execution(db, job)
    if not errors:
        job.status = "validated"
        db.commit()
        return True, []
    else:
        return False, errors

def execute_dry_run(db: Session, job_id: int) -> dict[str, Any]:
    """
    Executes a dry-run for the job: renders messages for all pending recipients,
    records SendLogs marked as 'success' (dry-run mode), and updates recipient/job statuses.
    No browser automation is called.
    """
    job = get_job(db, job_id)
    if not job:
        raise ValueError(f"Job ID {job_id} not found.")

    valid, errors = validate_job(db, job_id)
    if not valid:
        raise ValueError(f"Job validation failed: {'; '.join(errors)}")

    job.status = "running"
    db.commit()

    sent_count = 0
    failed_count = 0
    rendered_previews: list[dict[str, Any]] = []

    body = job.template_snapshot_body or (job.template.body if job.template else "")

    for recipient in job.recipients:
        if recipient.status not in ("pending", "failed"):
            continue

        contact = recipient.contact
        try:
            rendered = render_template(
                template_body=body,
                recipient_vars=recipient.variables,
                contact=contact,
            )
            log = SendLog(
                job_recipient_id=recipient.id,
                timestamp=utc_now(),
                rendered_text=rendered,
                outcome="success",
                error="DRY_RUN (No send performed)",
                retry_count=0,
            )
            db.add(log)
            recipient.status = "success"
            sent_count += 1
            rendered_previews.append(
                {
                    "recipient_id": recipient.id,
                    "contact": contact.display_name if contact else "Unknown",
                    "whatsapp_ref": contact.whatsapp_ref if contact else "Unknown",
                    "rendered_text": rendered,
                }
            )
        except Exception as e:
            log = SendLog(
                job_recipient_id=recipient.id,
                timestamp=utc_now(),
                rendered_text="",
                outcome="failure",
                error=str(e),
                retry_count=0,
            )
            db.add(log)
            recipient.status = "failed"
            failed_count += 1

    if failed_count == 0:
        job.status = "completed"
    elif sent_count > 0:
        job.status = "completed_with_errors"
    else:
        job.status = "failed"

    db.commit()

    return {
        "job_id": job.id,
        "status": job.status,
        "total_recipients": len(job.recipients),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "previews": rendered_previews,
    }

def retry_failed_recipients(db: Session, job_id: int) -> Job:
    """
    Resets status of failed recipients in a job back to 'pending'
    and updates job status back to 'validated' so it can be re-run.
    """
    job = get_job(db, job_id)
    if not job:
        raise ValueError(f"Job ID {job_id} not found.")

    failed_recipients = [r for r in job.recipients if r.status == "failed"]
    if not failed_recipients:
        raise ValueError("No failed recipients to retry in this job.")

    for r in failed_recipients:
        r.status = "pending"

    job.status = "validated"
    db.commit()
    db.refresh(job)
    return job
