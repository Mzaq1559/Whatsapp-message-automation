import csv
import io
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..data.models import Contact, Job, JobRecipient, SendLog


def get_job_summary_stats(db: Session, job_id: int) -> dict[str, Any]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return {}

    total = len(job.recipients)
    sent = sum(1 for r in job.recipients if r.status == "success")
    failed = sum(1 for r in job.recipients if r.status == "failed")
    skipped = sum(1 for r in job.recipients if r.status == "skipped")
    pending = sum(1 for r in job.recipients if r.status == "pending")

    return {
        "job_id": job.id,
        "job_name": job.name,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "total_recipients": total,
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "pending": pending,
    }

def get_dashboard_stats(db: Session) -> dict[str, Any]:
    total_jobs = db.query(Job).count()
    total_contacts = db.query(Contact).filter(Contact.archived_at.is_(None)).count()
    total_sends = db.query(SendLog).filter(SendLog.outcome == "success").count()
    total_failures = db.query(SendLog).filter(SendLog.outcome == "failure").count()

    recent_jobs = (
        db.query(Job).order_by(Job.created_at.desc()).limit(5).all()
    )

    recent_jobs_summary = [get_job_summary_stats(db, j.id) for j in recent_jobs]

    return {
        "total_jobs": total_jobs,
        "total_contacts": total_contacts,
        "total_sends": total_sends,
        "total_failures": total_failures,
        "recent_jobs": recent_jobs_summary,
    }

def query_send_logs(
    db: Session,
    job_id: int | None = None,
    contact_id: int | None = None,
    outcome: str | None = None,
    search: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """
    Returns (logs_list, total_count)
    """
    query = (
        db.query(SendLog, JobRecipient, Contact, Job)
        .join(JobRecipient, SendLog.job_recipient_id == JobRecipient.id)
        .join(Contact, JobRecipient.contact_id == Contact.id)
        .join(Job, JobRecipient.job_id == Job.id)
    )

    if job_id:
        query = query.filter(JobRecipient.job_id == job_id)
    if contact_id:
        query = query.filter(JobRecipient.contact_id == contact_id)
    if outcome:
        query = query.filter(SendLog.outcome == outcome)
    if start_date:
        query = query.filter(SendLog.timestamp >= start_date)
    if end_date:
        query = query.filter(SendLog.timestamp <= end_date)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (SendLog.rendered_text.ilike(search_term))
            | (Contact.display_name.ilike(search_term))
            | (Contact.whatsapp_ref.ilike(search_term))
        )

    total_count = query.count()
    results = (
        query.order_by(SendLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    logs_list = []
    for log, recipient, contact, job in results:
        logs_list.append(
            {
                "log_id": log.id,
                "job_id": job.id,
                "job_name": job.name,
                "recipient_id": recipient.id,
                "contact_id": contact.id,
                "contact_name": contact.display_name,
                "whatsapp_ref": contact.whatsapp_ref,
                "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                "rendered_text": log.rendered_text,
                "outcome": log.outcome,
                "error": log.error or "",
                "retry_count": log.retry_count,
            }
        )

    return logs_list, total_count

def export_send_logs_csv(
    db: Session,
    job_id: int | None = None,
    outcome: str | None = None,
) -> str:
    logs, _ = query_send_logs(db, job_id=job_id, outcome=outcome, limit=10000)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "log_id",
            "job_id",
            "job_name",
            "contact_id",
            "contact_name",
            "whatsapp_ref",
            "timestamp",
            "rendered_text",
            "outcome",
            "error",
            "retry_count",
        ],
    )
    writer.writeheader()

    for item in logs:
        row = {k: item[k] for k in writer.fieldnames if k in item}
        writer.writerow(row)

    return output.getvalue()
