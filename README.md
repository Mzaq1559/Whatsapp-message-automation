# WhatsApp Outreach Automation Platform

A single-user desktop/server tool that automates WhatsApp Web sessions to send templated, personalized messages to contacts and groups.

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│   Streamlit Frontend (UI)   │     │        CLI (Typer)          │
└──────────────┬───────────────┘     └──────────────┬───────────────┘
               │                                    │
               └─────────────────┬──────────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │      Core Engine        │  <- Shared Business Logic
                     │  (contacts, templates,   │
                     │   jobs, validation)       │
                     └────────────┬────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
┌───────▼────────┐     ┌──────────▼──────────┐   ┌───────────▼───────────┐
│   Data Layer   │     │  Automation Engine   │   │   Scheduler Process   │
│ SQLite+SQLAlchemy│    │  (Selenium driver,   │   │ (APScheduler, runs as │
│   + Alembic    │     │   send logic, retry) │   │  independent process) │
└────────────────┘     └──────────────────────┘   └───────────────────────┘
```

> [!IMPORTANT]
> **Strict Layering**: The Streamlit UI and CLI never talk to Selenium, the database, or the scheduler directly. All presentation layers strictly consume the Core Engine API.

---

## ✨ Features

- **Contacts & Groups Management**: Full CRUD, tags, notes, soft-delete archiving, and CSV bulk import wizard with deduplication.
- **Dynamic Templates**: Placeholders (`{var_name}`), live variable extraction, built-in dynamic variables (`{today}`, `{recipient_name}`), and live preview rendering.
- **Job Orchestration**: Step-by-step wizard, variable resolution, template snapshotting, dry-run simulation mode, live WhatsApp Web dispatch, failed recipient retries, and job cloning.
- **Safety Guardrails**: Configurable min-delay human pacing with randomized jitter, per-run hard caps, and rolling 24-hour send caps (Conservative & Standard presets).
- **Independent APScheduler**: Persisted SQLite job store surviving process restarts with misfire handling ("run_once" vs "skip").
- **Full Audit Logging**: Complete SendLog table tracking rendered text snapshots, success/failure outcomes, retry counts, error traces, and CSV export.
- **Two Presentation Interfaces**: Interactive Streamlit Dashboard UI +Typer CLI for scripting/server automation.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
- Python 3.11+
- Google Chrome Browser installed
- `uv` or `pip`

### 2. Clone & Install
```bash
git clone https://github.com/Mzaq1559/Whatsapp-message-automation.git
cd Whatsapp-message-automation

# Create virtual environment and install in editable mode with dev dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

---

## 🚀 Usage Guide

### First-Time WhatsApp Web Login (Heading Mode)
1. Launch the Streamlit UI:
   ```bash
   whatsapp-automation-ui
   ```
2. Navigate to **Settings & Safety** -> **Run Session Health Check**.
3. Scan the QR code in the opened Chrome window. The login session is saved in `~/.whatsapp_automation_chrome_profile` for all future headless or scheduled runs.

---

### Streamlit UI Interface
Launch the interactive web platform:
```bash
whatsapp-automation-ui
# or: streamlit run src/whatsapp_automation/ui/app.py
```
Navigation options:
- **📊 Dashboard**: Metrics overview, recent job runs, upcoming scheduled jobs.
- **📇 Contacts & Groups**: View, filter, create contacts, and bulk import CSVs.
- **📝 Templates**: Create templates with `{var}` placeholders and test live previews.
- **🚀 Compose Job**: Step-by-step wizard to build, preview, dry-run, launch, or schedule campaigns.
- **📜 Audit Logs & History**: Search logs, view rendered text, inspect failure errors, export CSV.
- **⚙️ Settings & Safety**: Adjust safety presets, rate limits, and run session health checks.

---

### Typer CLI Interface

#### Contacts
```bash
# List contacts
whatsapp-automation contacts list

# Add contact
whatsapp-automation contacts add --name "Alice" --ref "+1234567890" --tags "work,study"

# Import CSV
whatsapp-automation contacts import-csv contacts.csv --name-col "Name" --ref-col "Phone"
```

#### Templates
```bash
# Add template
whatsapp-automation templates add --name "Nudge" --body "Hi {recipient_name}, assignment {task} is due on {today}."

# List templates
whatsapp-automation templates list
```

#### Jobs & Execution
```bash
# Create job
whatsapp-automation jobs create --name "Weekly Nudge" --template-id 1 --contact-id 1 --contact-id 2

# Dry-run execution
whatsapp-automation jobs run --job-id 1 --dry-run

# Live execution via WhatsApp Web
whatsapp-automation jobs run --job-id 1 --live

# Retry failed recipients
whatsapp-automation jobs retry-failed --job-id 1
```

#### Audit History
```bash
# Query history logs
whatsapp-automation history list --status failed

# Export CSV log
whatsapp-automation history export --output send_history.csv
```

---

### Independent Scheduler Process
Run the background scheduler in a dedicated process/service:
```bash
whatsapp-automation-scheduler
```

---

## 🧪 Running Tests & Quality Checks

Run the automated pytest suite:
```bash
pytest
```

Run code formatting and type checking:
```bash
ruff check src/
mypy src/
```

---

## 🛡️ Safety & Anti-Detection Guidelines

- **Conservative Defaults**: Default min send delay of 10s + up to 5s randomized jitter.
- **Daily Caps**: Hard stop at 50 sends per 24 hours in Conservative mode.
- **No Spam / Cold Outreach**: This tool is designed strictly for opt-in personal contact circles and study/work groups.
