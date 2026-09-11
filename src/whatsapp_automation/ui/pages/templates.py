import streamlit as st

from ...core import templates as template_engine
from ...data.session import get_session


def render_templates_page():
    st.title("📝 Message Templates")
    st.caption("Create and manage message templates with dynamic variable placeholders like {name}, {deadline}, or built-ins like {today}.")

    db = get_session()
    try:
        tab1, tab2 = st.tabs(["📚 Saved Templates", "✨ Create / Edit Template"])

        with tab1:
            col1, col2 = st.columns([3, 1])
            search = col1.text_input("🔍 Search Templates", "")
            cat_filter = col2.text_input("🏷️ Category Filter", "")

            tmpls = template_engine.list_templates(
                db,
                search=search if search.strip() else None,
                category=cat_filter if cat_filter.strip() else None,
            )

            if tmpls:
                for t in tmpls:
                    with st.expander(f"📌 {t.name} (Category: {t.category})"):
                        all_vars = template_engine.extract_variables(t.body)
                        req_vars = template_engine.get_required_custom_variables(t.body)
                        st.markdown(f"**Detected Variables:** `{', '.join(all_vars)}`")
                        st.markdown(f"**Required Custom Variables:** `{', '.join(req_vars) if req_vars else 'None'}`")
                        st.text_area("Body", t.body, height=120, disabled=True, key=f"tmpl_body_{t.id}")

                        if st.button("Delete Template", key=f"del_tmpl_{t.id}"):
                            template_engine.delete_template(db, t.id)
                            st.success(f"Template '{t.name}' deleted.")
                            st.rerun()
            else:
                st.info("No templates found.")

        with tab2:
            st.subheader("Template Editor & Live Preview")

            t_name = st.text_input("Template Name", placeholder="e.g. Weekly Meeting Nudge")
            t_cat = st.text_input("Category", value="general", placeholder="e.g. reminders, study, birthday")
            t_body = st.text_area(
                "Template Body (use {variable_name} placeholders)",
                value="Hi {recipient_name}!\nThis is a reminder for our meeting on {date} at {room}.\nDate sent: {today}",
                height=180,
            )

            # Live Variable Detection
            st.divider()
            st.markdown("### 🔍 Live Variable Analysis")
            detected = template_engine.extract_variables(t_body)
            required_custom = template_engine.get_required_custom_variables(t_body)

            col_a, col_b = st.columns(2)
            col_a.info(f"**All Placeholders:** {', '.join(detected) if detected else 'None'}")
            col_b.warning(f"**Required Per-Recipient Variables:** {', '.join(required_custom) if required_custom else 'None (All built-in)'}")

            # Live Preview Section
            st.markdown("### 👁️ Live Preview Renderer")
            sample_vars = {}
            if required_custom:
                st.caption("Provide sample values to test rendering:")
                for var in required_custom:
                    sample_vars[var] = st.text_input(f"Sample '{var}'", f"Sample_{var}")

            try:
                preview_text = template_engine.render_template(
                    template_body=t_body,
                    recipient_vars=sample_vars,
                )
                st.code(preview_text, language="markdown")
            except Exception as e:
                st.error(f"Render Error: {e!s}")

            if st.button("Save Template", type="primary"):
                if not t_name.strip() or not t_body.strip():
                    st.error("Template Name and Body are required.")
                else:
                    tmpl = template_engine.create_template(
                        db, name=t_name, body=t_body, category=t_cat
                    )
                    st.success(f"Template '{tmpl.name}' saved successfully (ID: {tmpl.id})!")
                    st.rerun()

    finally:
        db.close()
