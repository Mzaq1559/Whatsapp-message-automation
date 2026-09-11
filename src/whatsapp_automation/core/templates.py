import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ..data.models import Contact, Template

BUILTIN_VARIABLES: set[str] = {"today", "recipient_name"}

def utc_now() -> datetime:
    return datetime.now(UTC)

def extract_variables(template_body: str) -> list[str]:
    """
    Find all placeholders in template body matching {var_name}.
    Filters out built-in variables like {today} and {recipient_name} from user-required variables,
    but returns all distinct variable names sorted.
    """
    matches = re.findall(r"\{([a-zA-Z0-9_]+)\}", template_body)
    # Deduplicate while preserving order of first appearance
    seen = set()
    vars_found = []
    for var in matches:
        if var not in seen:
            seen.add(var)
            vars_found.append(var)
    return vars_found

def get_required_custom_variables(template_body: str) -> list[str]:
    """Returns only custom variables that must be supplied by the user/recipient dict."""
    all_vars = extract_variables(template_body)
    return [v for v in all_vars if v not in BUILTIN_VARIABLES]

def render_template(
    template_body: str,
    recipient_vars: dict[str, Any],
    contact: Contact | None = None,
) -> str:
    """
    Renders a template body with recipient variables and built-in dynamic variables.
    """
    context: dict[str, Any] = {}

    # 1. Built-in variables
    context["today"] = datetime.now(UTC).strftime("%Y-%m-%d")
    if contact:
        context["recipient_name"] = contact.display_name
    else:
        context["recipient_name"] = recipient_vars.get("recipient_name", "")

    # 2. Custom recipient variables override or populate context
    for key, val in recipient_vars.items():
        context[key] = str(val) if val is not None else ""

    # Check for missing required variables
    all_req = get_required_custom_variables(template_body)
    missing = [v for v in all_req if v not in context or context[v] is None]
    if missing:
        raise ValueError(f"Missing required template variables: {', '.join(missing)}")

    # Format replacement
    rendered = template_body
    for key, val in context.items():
        rendered = rendered.replace(f"{{{key}}}", str(val))

    return rendered

def create_template(
    db: Session,
    name: str,
    body: str,
    category: str = "general",
) -> Template:
    template = Template(
        name=name.strip(),
        body=body,
        category=category.strip().lower(),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

def get_template(db: Session, template_id: int) -> Template | None:
    return db.query(Template).filter(Template.id == template_id).first()

def update_template(
    db: Session,
    template_id: int,
    name: str | None = None,
    body: str | None = None,
    category: str | None = None,
) -> Template | None:
    template = get_template(db, template_id)
    if not template:
        return None

    if name is not None:
        template.name = name.strip()
    if body is not None:
        template.body = body
    if category is not None:
        template.category = category.strip().lower()

    template.updated_at = utc_now()
    db.commit()
    db.refresh(template)
    return template

def delete_template(db: Session, template_id: int) -> bool:
    template = get_template(db, template_id)
    if not template:
        return False
    db.delete(template)
    db.commit()
    return True

def list_templates(
    db: Session,
    category: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Template]:
    query = db.query(Template)
    if category:
        query = query.filter(Template.category == category.strip().lower())
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (Template.name.ilike(search_term)) | (Template.body.ilike(search_term))
        )
    return query.order_by(Template.name.asc()).offset(offset).limit(limit).all()
