import json
import sys
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from ..automation import send as send_engine
from ..config.settings import SAFETY_MODE_PRESETS, settings
from ..core import contacts as contact_engine
from ..core import history as history_engine
from ..core import jobs as job_engine
from ..core import templates as template_engine
from ..data.session import get_session, init_db

app = typer.Typer(
    name="whatsapp-automation",
    help="WhatsApp Outreach Automation CLI Platform.",
    add_completion=False,
)

contacts_app = typer.Typer(help="Manage contacts and groups.")
templates_app = typer.Typer(help="Manage message templates.")
jobs_app = typer.Typer(help="Manage and run outreach jobs.")
schedule_app = typer.Typer(help="Manage scheduled runs.")
history_app = typer.Typer(help="Query audit logs and history.")
settings_app = typer.Typer(help="View and adjust platform settings.")

app.add_typer(contacts_app, name="contacts")
app.add_typer(templates_app, name="templates")
app.add_typer(jobs_app, name="jobs")
app.add_typer(schedule_app, name="schedule")
app.add_typer(history_app, name="history")
app.add_typer(settings_app, name="settings")

console = Console()

# --- CONTACTS COMMANDS ---
@contacts_app.command("list")
def list_contacts(
    tag: str | None = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    search: str | None = typer.Option(None, "--search", "-s", help="Search name/phone"),
    format_json: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    init_db()
    db = get_session()
    try:
        contacts = contact_engine.list_contacts(db, tag=tag, search=search)
        if format_json:
            data = [
                {
                    "id": c.id,
                    "display_name": c.display_name,
                    "whatsapp_ref": c.whatsapp_ref,
                    "is_group": c.is_group,
                    "tags": c.tags,
                }
                for c in contacts
            ]
            typer.echo(json.dumps(data, indent=2))
            return

        table = Table(title="Contacts & Groups")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="bold green")
        table.add_column("WhatsApp Ref", style="yellow")
        table.add_column("Type")
        table.add_column("Tags")

        for c in contacts:
            table.add_row(
                str(c.id),
                c.display_name,
                c.whatsapp_ref,
                "Group" if c.is_group else "Contact",
                ", ".join(c.tags),
            )
        console.print(table)
    finally:
        db.close()

@contacts_app.command("add")
def add_contact(
    name: str = typer.Option(..., "--name", "-n", help="Display name"),
    ref: str = typer.Option(..., "--ref", "-r", help="Phone number or group search name"),
    is_group: bool = typer.Option(False, "--group", help="Flag as WhatsApp group"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    notes: str | None = typer.Option(None, "--notes", help="Notes"),
):
    init_db()
    db = get_session()
    try:
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        contact = contact_engine.create_contact(
            db, display_name=name, whatsapp_ref=ref, is_group=is_group, tags=tag_list, notes=notes
        )
        console.print(f"[green]Successfully created contact ID {contact.id}: {contact.display_name}[/green]")
    finally:
        db.close()

@contacts_app.command("import-csv")
def import_csv(
    filepath: str = typer.Argument(..., help="Path to CSV file"),
    name_col: str = typer.Option("display_name", "--name-col", help="Column for name"),
    ref_col: str = typer.Option("whatsapp_ref", "--ref-col", help="Column for phone/ref"),
    tags_col: str = typer.Option("tags", "--tags-col", help="Column for tags"),
):
    init_db()
    db = get_session()
    try:
        mapping = {"display_name": name_col, "whatsapp_ref": ref_col, "tags": tags_col}
        result = contact_engine.bulk_import_csv(db, csv_text_or_path=filepath, column_mapping=mapping)
        console.print("[bold green]Import finished![/bold green]")
        console.print(f"Imported: {result['imported_count']} | Skipped Duplicates: {result['skipped_duplicates_count']}")
        if result["errors"]:
            console.print("[red]Errors:[/red]")
            for err in result["errors"]:
                console.print(f" - {err}")
    finally:
        db.close()

# --- TEMPLATES COMMANDS ---
@templates_app.command("list")
def list_templates(
    search: str | None = typer.Option(None, "--search", "-s"),
    format_json: bool = typer.Option(False, "--json"),
):
    init_db()
    db = get_session()
    try:
        templates = template_engine.list_templates(db, search=search)
        if format_json:
            data = [
                {
                    "id": t.id,
                    "name": t.name,
                    "body": t.body,
                    "category": t.category,
                    "variables": template_engine.extract_variables(t.body),
                }
                for t in templates
            ]
            typer.echo(json.dumps(data, indent=2))
            return

        table = Table(title="Templates")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="bold green")
        table.add_column("Category", style="magenta")
        table.add_column("Variables", style="yellow")
        table.add_column("Body Preview")

        for t in templates:
            vars_str = ", ".join(template_engine.extract_variables(t.body))
            preview = t.body[:40] + ("..." if len(t.body) > 40 else "")
            table.add_row(str(t.id), t.name, t.category, vars_str, preview)
        console.print(table)
    finally:
        db.close()

@templates_app.command("add")
def add_template(
    name: str = typer.Option(..., "--name", "-n"),
    body: str = typer.Option(..., "--body", "-b"),
    category: str = typer.Option("general", "--category", "-c"),
):
    init_db()
    db = get_session()
    try:
        tmpl = template_engine.create_template(db, name=name, body=body, category=category)
        req_vars = template_engine.get_required_custom_variables(body)
        console.print(f"[green]Created template ID {tmpl.id}: {tmpl.name}[/green]")
        console.print(f"Detected required custom variables: {req_vars}")
    finally:
        db.close()

# --- JOBS COMMANDS ---
@jobs_app.command("create")
def create_job(
    name: str = typer.Option(..., "--name", "-n"),
    template_id: int = typer.Option(..., "--template-id", "-t"),
    contacts: List[int] = typer.Option(None, "--contact-id", "-c", help="Recipient contact IDs"),
    safety_mode: str = typer.Option("Conservative", "--safety-mode"),
):
    init_db()
    db = get_session()
    try:
        recipient_data = [{"contact_id": cid, "variables": {}} for cid in contacts]
        job = job_engine.create_job(
            db, name=name, template_id=template_id, recipient_data=recipient_data, safety_mode=safety_mode
        )
        console.print(f"[bold green]Job created successfully! ID: {job.id}, Status: {job.status}[/bold green]")
    finally:
        db.close()

@jobs_app.command("list")
def list_jobs(
    status: str | None = typer.Option(None, "--status"),
    format_json: bool = typer.Option(False, "--json"),
):
    init_db()
    db = get_session()
    try:
        jobs = job_engine.list_jobs(db, status=status)
        if format_json:
            data = [
                {
                    "id": j.id,
                    "name": j.name,
                    "template_id": j.template_id,
                    "status": j.status,
                    "recipients_count": len(j.recipients),
                    "created_at": j.created_at.isoformat(),
                }
                for j in jobs
            ]
            typer.echo(json.dumps(data, indent=2))
            return

        table = Table(title="Outreach Jobs")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="bold green")
        table.add_column("Status", style="yellow")
        table.add_column("Recipients")
        table.add_column("Safety Mode")
        table.add_column("Created At")

        for j in jobs:
            table.add_row(
                str(j.id),
                j.name,
                j.status,
                str(len(j.recipients)),
                j.safety_mode,
                j.created_at.strftime("%Y-%m-%d %H:%M"),
            )
        console.print(table)
    finally:
        db.close()

@jobs_app.command("run")
def run_job(
    job_id: int = typer.Option(..., "--job-id", "-j"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run in dry-run simulation mode"),
    live: bool = typer.Option(False, "--live", help="Run live via Selenium"),
    format_json: bool = typer.Option(False, "--json"),
):
    if not dry_run and not live:
        console.print("[red]Error: You must specify either --dry-run or --live[/red]")
        sys.exit(1)

    init_db()
    db = get_session()
    try:
        if dry_run:
            result = job_engine.execute_dry_run(db, job_id=job_id)
        else:
            result = send_engine.execute_live_job(db, job_id=job_id, headless=True)

        if format_json:
            typer.echo(json.dumps(result, indent=2))
        else:
            console.print("[bold green]Job execution completed![/bold green]")
            console.print(f"Status: {result['status']} | Total: {result['total_recipients']} | Sent: {result['sent_count']} | Failed: {result['failed_count']}")

        if result.get("failed_count", 0) > 0 or result.get("status") == "failed":
            sys.exit(1)
        else:
            sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Execution Error: {e!s}[/bold red]")
        sys.exit(1)
    finally:
        db.close()

@jobs_app.command("retry-failed")
def retry_failed(job_id: int = typer.Option(..., "--job-id", "-j")):
    init_db()
    db = get_session()
    try:
        job = job_engine.retry_failed_recipients(db, job_id=job_id)
        console.print(f"[green]Job ID {job.id} failed recipients reset to pending. Job status: {job.status}[/green]")
    finally:
        db.close()

# --- HISTORY COMMANDS ---
@history_app.command("list")
def list_history(
    job_id: int | None = typer.Option(None, "--job"),
    outcome: str | None = typer.Option(None, "--status"),
    format_json: bool = typer.Option(False, "--json"),
):
    init_db()
    db = get_session()
    try:
        logs, total = history_engine.query_send_logs(db, job_id=job_id, outcome=outcome)
        if format_json:
            typer.echo(json.dumps(logs, indent=2))
            return

        table = Table(title=f"Send History Logs (Total: {total})")
        table.add_column("Log ID", style="cyan")
        table.add_column("Timestamp")
        table.add_column("Job Name")
        table.add_column("Recipient", style="bold green")
        table.add_column("Outcome", style="magenta")
        table.add_column("Error", style="red")

        for log in logs:
            table.add_row(
                str(log["log_id"]),
                log["timestamp"],
                log["job_name"],
                log["contact_name"],
                log["outcome"],
                log["error"][:30] + ("..." if len(log["error"]) > 30 else ""),
            )
        console.print(table)
    finally:
        db.close()

@history_app.command("export")
def export_history(
    job_id: int | None = typer.Option(None, "--job"),
    outfile: str = typer.Option("send_history.csv", "--output", "-o"),
):
    init_db()
    db = get_session()
    try:
        csv_data = history_engine.export_send_logs_csv(db, job_id=job_id)
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(csv_data)
        console.print(f"[green]Exported history to {outfile}[/green]")
    finally:
        db.close()

# --- SETTINGS COMMANDS ---
@settings_app.command("show")
def show_settings():
    table = Table(title="Platform Settings")
    table.add_column("Setting Key", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("WHATSAPP_WEB_URL", settings.whatsapp_web_url)
    table.add_row("DB_URL", settings.db_url)
    table.add_row("CHROME_PROFILE_DIR", settings.chrome_profile_dir)
    table.add_row("HEADLESS", str(settings.headless))
    table.add_row("SAFETY_MODE", settings.safety_mode)
    table.add_row("MIN_SEND_DELAY", f"{settings.min_send_delay}s")
    table.add_row("MAX_JITTER", f"{settings.max_jitter}s")
    table.add_row("MAX_SENDS_PER_RUN", str(settings.max_sends_per_run))
    table.add_row("MAX_SENDS_PER_24H", str(settings.max_sends_per_24h))

    console.print(table)

@settings_app.command("set-safety")
def set_safety_mode(mode: str = typer.Argument(..., help="Conservative or Standard")):
    if mode not in SAFETY_MODE_PRESETS:
        console.print(f"[red]Invalid mode. Allowed: {list(SAFETY_MODE_PRESETS.keys())}[/red]")
        sys.exit(1)

    settings.apply_safety_preset(mode)
    console.print(f"[green]Applied safety mode preset: {mode}[/green]")

if __name__ == "__main__":
    app()
