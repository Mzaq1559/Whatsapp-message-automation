import pandas as pd
import streamlit as st

from ...automation import send as send_engine
from ...core import contacts as contact_engine
from ...core import jobs as job_engine
from ...core import templates as template_engine
from ...data.session import get_session
from ...scheduler import scheduler as scheduler_engine


def render_compose_page():
    st.title("🚀 Compose Outreach Job")
    st.caption("Step-based wizard to select templates, pick recipients, fill variables, preview messages, and launch campaigns.")

    db = get_session()
    try:
        # Step 1: Select Template
        st.subheader("Step 1: Choose Message Template")
        all_templates = template_engine.list_templates(db, limit=200)
        if not all_templates:
            st.warning("No templates found. Please create a template first in the 'Templates' section.")
            return

        tmpl_options = {f"{t.name} (ID: {t.id})": t for t in all_templates}
        selected_tmpl_name = st.selectbox("Select Template", list(tmpl_options.keys()))
        selected_tmpl = tmpl_options[selected_tmpl_name]

        required_vars = template_engine.get_required_custom_variables(selected_tmpl.body)
        st.info(f"Selected Template: **{selected_tmpl.name}** | Required Variables: `{', '.join(required_vars) if required_vars else 'None'}`")

        st.divider()

        # Step 2: Select Recipients
        st.subheader("Step 2: Select Recipients")
        recip_source = st.radio("Recipient Selection Mode", ["Manual / Tag Selection", "CSV Upload with Variables"], horizontal=True)

        selected_contacts = []
        recipient_variable_data = []

        if recip_source == "Manual / Tag Selection":
            all_contacts = contact_engine.list_contacts(db, limit=500)
            tag_filter = st.text_input("Filter Contacts by Tag (optional)", "")

            filtered_contacts = all_contacts
            if tag_filter.strip():
                filtered_contacts = [c for c in all_contacts if tag_filter.strip().lower() in c.tags]

            contact_dict = {f"{c.display_name} ({c.whatsapp_ref}) [ID: {c.id}]": c for c in filtered_contacts}
            selected_keys = st.multiselect("Select Recipients", list(contact_dict.keys()), default=list(contact_dict.keys())[:5])
            selected_contacts = [contact_dict[k] for k in selected_keys]

            st.divider()
            # Step 3: Fill Per-Recipient Variables
            st.subheader("Step 3: Fill Per-Recipient Variables")
            if required_vars and selected_contacts:
                st.caption("Provide variable values for each selected recipient:")
                for c in selected_contacts:
                    st.markdown(f"**{c.display_name}** (`{c.whatsapp_ref}`)")
                    c_vars = {}
                    cols = st.columns(len(required_vars))
                    for idx, v_name in enumerate(required_vars):
                        val = cols[idx].text_input(f"'{v_name}' for {c.display_name}", key=f"var_{c.id}_{v_name}")
                        c_vars[v_name] = val
                    recipient_variable_data.append({"contact_id": c.id, "variables": c_vars, "contact": c})
            else:
                for c in selected_contacts:
                    recipient_variable_data.append({"contact_id": c.id, "variables": {}, "contact": c})

        else: # CSV Upload
            csv_file = st.file_uploader("Upload CSV containing recipients & variable values", type=["csv"])
            if csv_file:
                df = pd.read_csv(csv_file)
                st.dataframe(df.head(), use_container_width=True)
                cols = list(df.columns)

                ref_col = st.selectbox("WhatsApp Identifier / Phone Column", cols)

                # Match contacts in DB or create on the fly
                for idx, row in df.iterrows():
                    ref_val = str(row[ref_col]).strip()
                    matched = contact_engine.detect_duplicate(db, display_name=ref_val, whatsapp_ref=ref_val)
                    if not matched:
                        matched = contact_engine.create_contact(db, display_name=ref_val, whatsapp_ref=ref_val)

                    row_vars = {v: str(row[v]) for v in required_vars if v in row}
                    recipient_variable_data.append({"contact_id": matched.id, "variables": row_vars, "contact": matched})

                st.success(f"Parsed {len(recipient_variable_data)} recipients from CSV.")

        if not recipient_variable_data:
            st.warning("Please select at least 1 recipient to proceed.")
            return

        st.divider()

        # Step 4: Message Preview
        st.subheader("Step 4: Rendered Messages Preview")
        previews = []
        for r_item in recipient_variable_data:
            c = r_item["contact"]
            try:
                rendered = template_engine.render_template(
                    template_body=selected_tmpl.body,
                    recipient_vars=r_item["variables"],
                    contact=c,
                )
                previews.append({"Recipient": c.display_name, "WhatsApp Ref": c.whatsapp_ref, "Rendered Message": rendered})
            except Exception as e:
                previews.append({"Recipient": c.display_name, "WhatsApp Ref": c.whatsapp_ref, "Rendered Message": f"ERROR: {e!s}"})

        st.dataframe(pd.DataFrame(previews), use_container_width=True)

        st.divider()

        # Step 5: Execution Mode & Launch Confirmation
        st.subheader("Step 5: Job Execution Configuration")
        job_name = st.text_input("Job / Campaign Name *", f"Outreach - {selected_tmpl.name}")
        safety_mode = st.selectbox("Safety Preset Mode", ["Conservative", "Standard"], index=0)

        exec_mode = st.radio("Execution Mode", ["Dry-Run (Simulation & Preview Log Only)", "Run Now (Live WhatsApp Send)", "Schedule for Later"], horizontal=True)

        schedule_expr = ""
        if exec_mode == "Schedule for Later":
            schedule_expr = st.text_input("Cron expression (e.g. '0 9 * * 1') or Datetime (ISO format '2026-10-01T09:00:00')", "0 9 * * 1")

        # Explicit confirmation checkbox for live execution (FR-8.7)
        confirm_run = True
        if exec_mode == "Run Now (Live WhatsApp Send)":
            confirm_run = st.checkbox("⚠️ I confirm launching live WhatsApp message sending to real contacts.")

        if st.button("🚀 Submit Job", type="primary", disabled=(not confirm_run)):
            if not job_name.strip():
                st.error("Job Name is required.")
                return

            # Create Job
            job = job_engine.create_job(
                db=db,
                name=job_name,
                template_id=selected_tmpl.id,
                recipient_data=[{"contact_id": r["contact_id"], "variables": r["variables"]} for r in recipient_variable_data],
                safety_mode=safety_mode,
            )

            if exec_mode.startswith("Dry-Run"):
                res = job_engine.execute_dry_run(db, job_id=job.id)
                st.success(f"Dry-run executed successfully! Status: {res['status']} | Total: {res['total_recipients']} | Previews logged to history.")
            elif exec_mode.startswith("Run Now"):
                st.info("Launching live WhatsApp Web automation...")
                res = send_engine.execute_live_job(db, job_id=job.id, headless=True)
                if res["status"] == "completed":
                    st.success(f"Live job completed successfully! Sent: {res['sent_count']}")
                else:
                    st.warning(f"Live job finished with status: {res['status']} | Sent: {res['sent_count']} | Failed: {res['failed_count']}")
            elif exec_mode == "Schedule for Later":
                s_run = scheduler_engine.add_scheduled_run(
                    db=db, job_id=job.id, cron_or_datetime=schedule_expr, live=True
                )
                st.success(f"Scheduled job successfully! Scheduled Run ID: {s_run.id}")

    finally:
        db.close()
