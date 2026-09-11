from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..config.settings import SAFETY_MODE_PRESETS, settings
from ..data.models import Job, SendLog
from .templates import get_required_custom_variables


def utc_now() -> datetime:
    return datetime.now(UTC)

def validate_job_recipients_variables(
    job_body: str, recipients: list[tuple[int, dict[str, Any]]]
) -> list[str]:
    """
    Validates that every recipient has all required custom variables.
    recipients is a list of (contact_id, variables_dict).
    Returns list of error messages (empty if valid).
    """
    required_vars = get_required_custom_variables(job_body)
    errors: list[str] = []

    for contact_id, vars_dict in recipients:
        missing = [v for v in required_vars if v not in vars_dict or vars_dict[v] is None or str(vars_dict[v]).strip() == ""]
        if missing:
            errors.append(f"Contact ID {contact_id} missing variables: {', '.join(missing)}")

    return errors

def check_rolling_24h_limit(db: Session, proposed_send_count: int, safety_mode: str) -> tuple[bool, str]:
    """
    Checks if sending `proposed_send_count` messages will breach the rolling 24h limit.
    """
    preset = SAFETY_MODE_PRESETS.get(safety_mode, {
        "max_sends_per_24h": settings.max_sends_per_24h,
        "max_sends_per_run": settings.max_sends_per_run,
    })
    max_24h = preset["max_sends_per_24h"]

    cutoff = utc_now() - timedelta(hours=24)
    past_24h_sends = (
        db.query(SendLog)
        .filter(SendLog.timestamp >= cutoff, SendLog.outcome == "success")
        .count()
    )

    total_projected = past_24h_sends + proposed_send_count
    if total_projected > max_24h:
        return (
            False,
            f"Rolling 24h limit reached: {past_24h_sends} sent in last 24h + {proposed_send_count} requested exceeds max cap of {max_24h}.",
        )
    return True, "24h limit check passed."

def check_max_sends_per_run(proposed_send_count: int, safety_mode: str) -> tuple[bool, str]:
    """
    Checks if `proposed_send_count` exceeds max sends allowed in a single run.
    """
    preset = SAFETY_MODE_PRESETS.get(safety_mode, {
        "max_sends_per_run": settings.max_sends_per_run,
    })
    max_per_run = preset["max_sends_per_run"]

    if proposed_send_count > max_per_run:
        return (
            False,
            f"Run cap exceeded: {proposed_send_count} recipients exceeds max allowed per run cap of {max_per_run}.",
        )
    return True, "Per-run cap check passed."

def validate_job_for_execution(db: Session, job: Job) -> list[str]:
    """
    Full pre-send validation for a job before live or dry-run execution.
    """
    errors: list[str] = []

    if not job.recipients:
        errors.append("Job has zero recipients.")
        return errors

    # Check recipient variable completion
    recipients_data = [(r.contact_id, r.variables) for r in job.recipients]
    body = job.template_snapshot_body or (job.template.body if job.template else "")
    var_errors = validate_job_recipients_variables(body, recipients_data)
    errors.extend(var_errors)

    # Check run caps
    run_cap_ok, run_cap_msg = check_max_sends_per_run(len(job.recipients), job.safety_mode)
    if not run_cap_ok:
        errors.append(run_cap_msg)

    # Check 24h rolling limit
    limit_ok, limit_msg = check_rolling_24h_limit(db, len(job.recipients), job.safety_mode)
    if not limit_ok:
        errors.append(limit_msg)

    return errors
