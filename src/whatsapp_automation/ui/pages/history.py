import streamlit as st

from ...core import history as history_engine
from ...core import jobs as job_engine
from ...data.session import get_session


def render_history_page():
    st.title("📜 Audit Logs & Send History")
    st.caption("Full audit log of every send attempt with rendered message snapshots, status outcomes, and failure trace details.")

    db = get_session()
    try:
        col1, col2, col3 = st.columns(3)
        status_filter = col1.selectbox("Filter Outcome Status", ["All", "success", "failure", "skipped"])
        search_query = col2.text_input("🔍 Search Message / Contact Name", "")
        page_size = col3.number_input("Rows Per Page", min_value=10, max_value=500, value=50)

        status_param = status_filter if status_filter != "All" else None

        logs, total = history_engine.query_send_logs(
            db,
            outcome=status_param,
            search=search_query if search_query.strip() else None,
            limit=int(page_size),
        )

        st.markdown(f"**Total Records Found:** `{total}`")

        # CSV Export Button
        csv_data = history_engine.export_send_logs_csv(db, outcome=status_param)
        st.download_button(
            label="📥 Export History as CSV",
            data=csv_data,
            file_name="whatsapp_send_history.csv",
            mime="text/csv",
        )

        st.divider()

        if logs:
            for item in logs:
                outcome_color = "🟢" if item["outcome"] == "success" else "🔴"
                with st.expander(
                    f"{outcome_color} Log #{item['log_id']} | Job: '{item['job_name']}' | Recipient: {item['contact_name']} ({item['whatsapp_ref']}) | Time: {item['timestamp']}"
                ):
                    st.markdown(f"**Outcome:** `{item['outcome']}` | **Retry Count:** `{item['retry_count']}`")
                    st.markdown("**Rendered Message Text:**")
                    st.code(item["rendered_text"], language="markdown")
                    if item["error"]:
                        st.markdown("**Error Details:**")
                        st.error(item["error"])

                    if item["outcome"] == "failure" and st.button(
                        "Retry Failed Recipients for this Job",
                        key=f"retry_job_{item['job_id']}_{item['log_id']}",
                    ):
                        job_engine.retry_failed_recipients(db, item["job_id"])
                        st.success(f"Reset failed recipients for Job ID {item['job_id']}. You can re-run it now.")
                        st.rerun()
        else:
            st.info("No audit logs found matching criteria.")

    finally:
        db.close()
