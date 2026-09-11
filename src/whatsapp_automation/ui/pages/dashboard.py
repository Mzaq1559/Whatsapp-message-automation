import streamlit as st

from ...core.history import get_dashboard_stats
from ...data.session import get_session
from ...scheduler.scheduler import list_scheduled_runs


def render_dashboard():
    st.title("📊 WhatsApp Outreach Dashboard")
    st.caption("Overview of system state, recent campaign runs, and background scheduler status.")

    db = get_session()
    try:
        stats = get_dashboard_stats(db)

        # Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Contacts", stats["total_contacts"])
        col2.metric("Total Jobs", stats["total_jobs"])
        col3.metric("Successful Sends", stats["total_sends"])
        col4.metric("Failed Sends", stats["total_failures"], delta_color="inverse")

        st.divider()

        st.subheader("🚀 Recent Job Runs")
        recent = stats["recent_jobs"]
        if recent:
            st.dataframe(
                recent,
                use_container_width=True,
                column_config={
                    "job_id": "Job ID",
                    "job_name": "Job Name",
                    "status": "Status",
                    "total_recipients": "Total Recipients",
                    "sent": "Sent",
                    "failed": "Failed",
                    "created_at": "Created At",
                },
            )
        else:
            st.info("No job runs recorded yet. Go to 'Compose Job' to start your first campaign!")

        st.divider()

        st.subheader("⏰ Upcoming Scheduled Runs")
        scheduled = list_scheduled_runs(db)
        if scheduled:
            st.dataframe(scheduled, use_container_width=True)
        else:
            st.info("No active scheduled jobs.")

    finally:
        db.close()
