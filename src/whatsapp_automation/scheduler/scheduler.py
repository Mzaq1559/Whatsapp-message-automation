import logging
import time
from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session

from ..automation.send import execute_live_job
from ..config.settings import settings
from ..core.jobs import execute_dry_run
from ..data.models import Job, ScheduledRun
from ..data.session import get_session, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_scheduler")

_scheduler: BackgroundScheduler | None = None

def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        # Use SQLAlchemy job store for persistence
        jobstores = {
            "default": {
                "type": "sqlalchemy",
                "url": settings.db_url,
            }
        }
        _scheduler = BackgroundScheduler(
            jobstores=jobstores,
            timezone=settings.scheduler_timezone,
        )
    return _scheduler

def _execute_scheduled_job_callback(job_id: int, live: bool = True) -> None:
    logger.info(f"Triggering scheduled job ID {job_id} (live={live})")
    session = get_session()
    try:
        if live:
            result = execute_live_job(db=session, job_id=job_id, headless=True)
        else:
            result = execute_dry_run(db=session, job_id=job_id)
        logger.info(f"Scheduled job ID {job_id} finished with status: {result.get('status')}")
    except Exception as e:
        logger.error(f"Error executing scheduled job ID {job_id}: {e!s}", exc_info=True)
    finally:
        session.close()

def add_scheduled_run(
    db: Session,
    job_id: int,
    cron_or_datetime: str,
    misfire_policy: str = "run_once",
    live: bool = True,
) -> ScheduledRun:
    """
    Schedules a job via cron expression (e.g. '0 9 * * 1') or ISO datetime string (e.g. '2026-10-01T09:00:00').
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job ID {job_id} not found.")

    misfire_grace = 3600 if misfire_policy == "run_once" else 1

    scheduled_run = ScheduledRun(
        job_id=job_id,
        cron_or_datetime=cron_or_datetime.strip(),
        timezone=settings.scheduler_timezone,
        misfire_policy=misfire_policy,
        paused=False,
    )
    db.add(scheduled_run)
    db.commit()
    db.refresh(scheduled_run)

    scheduler = get_scheduler()
    aps_job_id = f"job_run_{scheduled_run.id}"

    # Determine trigger type
    if cron_or_datetime.startswith("cron:") or " " in cron_or_datetime:
        expr = cron_or_datetime.replace("cron:", "").strip()
        parts = expr.split()
        if len(parts) == 5:
            trigger = CronTrigger.from_crontab(expr, timezone=settings.scheduler_timezone)
        else:
            raise ValueError(f"Invalid cron expression: '{expr}'. Expected 5 space-separated fields.")
    else:
        # Datetime string
        dt = datetime.fromisoformat(cron_or_datetime.replace("Z", "+00:00"))
        trigger = DateTrigger(run_date=dt, timezone=settings.scheduler_timezone)

    if scheduler.running:
        aps_job = scheduler.add_job(
            _execute_scheduled_job_callback,
            trigger=trigger,
            args=[job_id, live],
            id=aps_job_id,
            misfire_grace_time=misfire_grace,
            replace_existing=True,
        )
        if aps_job and hasattr(aps_job, "next_run_time") and aps_job.next_run_time:
            scheduled_run.next_fire_time = aps_job.next_run_time
            db.commit()

    job.status = "scheduled"
    db.commit()

    return scheduled_run

def pause_scheduled_run(db: Session, scheduled_run_id: int) -> bool:
    sr = db.query(ScheduledRun).filter(ScheduledRun.id == scheduled_run_id).first()
    if not sr:
        return False
    sr.paused = True
    db.commit()

    scheduler = get_scheduler()
    aps_job_id = f"job_run_{sr.id}"
    if scheduler.running and scheduler.get_job(aps_job_id):
        scheduler.pause_job(aps_job_id)

    return True

def resume_scheduled_run(db: Session, scheduled_run_id: int) -> bool:
    sr = db.query(ScheduledRun).filter(ScheduledRun.id == scheduled_run_id).first()
    if not sr:
        return False
    sr.paused = False
    db.commit()

    scheduler = get_scheduler()
    aps_job_id = f"job_run_{sr.id}"
    if scheduler.running and scheduler.get_job(aps_job_id):
        scheduler.resume_job(aps_job_id)

    return True

def cancel_scheduled_run(db: Session, scheduled_run_id: int) -> bool:
    sr = db.query(ScheduledRun).filter(ScheduledRun.id == scheduled_run_id).first()
    if not sr:
        return False

    scheduler = get_scheduler()
    aps_job_id = f"job_run_{sr.id}"
    if scheduler.running and scheduler.get_job(aps_job_id):
        scheduler.remove_job(aps_job_id)

    db.delete(sr)
    db.commit()
    return True

def list_scheduled_runs(db: Session) -> list[dict[str, Any]]:
    runs = db.query(ScheduledRun).all()
    results = []
    for r in runs:
        results.append(
            {
                "id": r.id,
                "job_id": r.job_id,
                "job_name": r.job.name if r.job else "Unknown",
                "cron_or_datetime": r.cron_or_datetime,
                "timezone": r.timezone,
                "next_fire_time": r.next_fire_time.isoformat() if r.next_fire_time else "N/A",
                "misfire_policy": r.misfire_policy,
                "paused": r.paused,
            }
        )
    return results

def main() -> None:
    """Standalone background scheduler process entry point."""
    logger.info("Starting WhatsApp Automation Independent Scheduler Process...")
    init_db()
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("Scheduler started successfully. Press Ctrl+C to exit.")

    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping Scheduler...")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
