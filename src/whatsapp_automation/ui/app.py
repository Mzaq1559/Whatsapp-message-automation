import streamlit as st

from whatsapp_automation.data.session import init_db
from whatsapp_automation.ui.pages.compose import render_compose_page
from whatsapp_automation.ui.pages.contacts import render_contacts_page
from whatsapp_automation.ui.pages.dashboard import render_dashboard
from whatsapp_automation.ui.pages.history import render_history_page
from whatsapp_automation.ui.pages.settings import render_settings_page
from whatsapp_automation.ui.pages.templates import render_templates_page

st.set_page_config(
    page_title="WhatsApp Outreach Automation",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS styling for premium look and feel
st.markdown(
    """
    <style>
    .main {
        background-color: #0E1117;
    }
    .stMetric {
        background-color: #1E232A;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stSidebarNav"] {
        padding-top: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def main():
    # Ensure database tables exist
    init_db()

    st.sidebar.title("💬 WhatsApp Outreach")
    st.sidebar.caption("Single-user Automation Engine v1.0")

    page = st.sidebar.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📇 Contacts & Groups",
            "📝 Templates",
            "🚀 Compose Job",
            "📜 Audit Logs & History",
            "⚙️ Settings & Safety",
        ],
    )

    st.sidebar.divider()
    st.sidebar.info("🔒 **Safety Mode:** Active\nRespecting rate limits and human pacing.")

    if page == "📊 Dashboard":
        render_dashboard()
    elif page == "📇 Contacts & Groups":
        render_contacts_page()
    elif page == "📝 Templates":
        render_templates_page()
    elif page == "🚀 Compose Job":
        render_compose_page()
    elif page == "📜 Audit Logs & History":
        render_history_page()
    elif page == "⚙️ Settings & Safety":
        render_settings_page()

if __name__ == "__main__":
    main()
