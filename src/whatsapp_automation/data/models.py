import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utc_now() -> datetime:
    return datetime.now(UTC)

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(255), nullable=False, index=True)
    whatsapp_ref = Column(String(255), nullable=False, index=True)  # Phone number or group name
    is_group = Column(Boolean, default=False, nullable=False)
    tags_raw = Column("tags", Text, default="[]")  # JSON encoded list of strings
    notes = Column(Text, nullable=True)
    archived_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    job_recipients = relationship("JobRecipient", back_populates="contact")

    @property
    def tags(self) -> list[str]:
        if not self.tags_raw:
            return []
        try:
            return json.loads(self.tags_raw)
        except Exception:
            return []

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self.tags_raw = json.dumps(value or [])

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    body = Column(Text, nullable=False)
    category = Column(String(100), default="general", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    jobs = relationship("Job", back_populates="template")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    template_snapshot_body = Column(Text, nullable=True)  # Render snapshot protection
    status = Column(String(50), default="draft", nullable=False, index=True)
    safety_mode = Column(String(50), default="Conservative", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    template = relationship("Template", back_populates="jobs")
    recipients = relationship("JobRecipient", back_populates="job", cascade="all, delete-orphan")
    scheduled_runs = relationship("ScheduledRun", back_populates="job", cascade="all, delete-orphan")

class JobRecipient(Base):
    __tablename__ = "job_recipients"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    variables_raw = Column("variables", Text, default="{}")  # JSON dict of per-recipient variables
    status = Column(String(50), default="pending", nullable=False, index=True)

    job = relationship("Job", back_populates="recipients")
    contact = relationship("Contact", back_populates="job_recipients")
    send_logs = relationship("SendLog", back_populates="job_recipient", cascade="all, delete-orphan")

    @property
    def variables(self) -> dict[str, Any]:
        if not self.variables_raw:
            return {}
        try:
            return json.loads(self.variables_raw)
        except Exception:
            return {}

    @variables.setter
    def variables(self, value: dict[str, Any]) -> None:
        self.variables_raw = json.dumps(value or {})

class SendLog(Base):
    __tablename__ = "send_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_recipient_id = Column(Integer, ForeignKey("job_recipients.id"), nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    rendered_text = Column(Text, nullable=False)
    outcome = Column(String(50), nullable=False)  # success, failure, skipped
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    job_recipient = relationship("JobRecipient", back_populates="send_logs")

class ScheduledRun(Base):
    __tablename__ = "scheduled_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    cron_or_datetime = Column(String(255), nullable=False)
    timezone = Column(String(100), default="UTC", nullable=False)
    next_fire_time = Column(DateTime, nullable=True)
    misfire_policy = Column(String(50), default="run_once", nullable=False)  # run_once or skip
    paused = Column(Boolean, default=False, nullable=False)

    job = relationship("Job", back_populates="scheduled_runs")

class RuntimeSetting(Base):
    __tablename__ = "runtime_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
