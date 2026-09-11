import streamlit as st

from ...automation.driver import check_session_health, close_driver, init_driver
from ...config.settings import settings


def render_settings_page():
    st.title("⚙️ Platform Settings & Safety Guardrails")
    st.caption("Configure rate limits, safety mode presets, Chrome profile paths, and verify WhatsApp session health.")

    st.subheader("🛡️ Safety Mode Presets")
    current_preset = settings.safety_mode
    selected_preset = st.selectbox("Select Preset Mode", ["Conservative", "Standard"], index=0 if current_preset == "Conservative" else 1)

    if st.button("Apply Selected Preset"):
        settings.apply_safety_preset(selected_preset)
        st.success(f"Applied '{selected_preset}' safety preset configuration.")
        st.rerun()

    st.divider()

    st.subheader("🎛️ Active Rate Limit & Cap Values")
    col1, col2 = st.columns(2)
    min_delay = col1.number_input("Minimum Send Delay (seconds)", value=float(settings.min_send_delay), min_value=1.0, step=1.0)
    jitter = col2.number_input("Max Jitter Delay (seconds)", value=float(settings.max_jitter), min_value=0.0, step=0.5)

    col3, col4 = st.columns(2)
    max_run = col3.number_input("Max Sends Per Run (Hard Cap)", value=int(settings.max_sends_per_run), min_value=1)
    max_24h = col4.number_input("Max Sends Per 24h Rolling Window", value=int(settings.max_sends_per_24h), min_value=1)

    if st.button("Save Custom Limits"):
        settings.min_send_delay = min_delay
        settings.max_jitter = jitter
        settings.max_sends_per_run = max_run
        settings.max_sends_per_24h = max_24h
        settings.safety_mode = "Custom"
        st.success("Custom rate limits updated successfully.")

    st.divider()

    st.subheader("🌐 Browser & Environment Configuration")
    st.text_input("WhatsApp Web URL (Read-only)", value=settings.whatsapp_web_url, disabled=True)
    st.text_input("Database URL (Read-only)", value=settings.db_url, disabled=True)
    st.text_input("Chrome User Data Directory Path", value=settings.chrome_profile_dir, disabled=True)

    st.divider()

    st.subheader("🔐 WhatsApp Web Session Health Status")
    st.info("The Chrome profile preserves your QR login session. Use the button below to test if your session is active.")

    if st.button("Run Session Health Check"):
        with st.spinner("Launching Chrome to verify WhatsApp Web login session..."):
            driver = None
            try:
                driver = init_driver(headless=False)
                driver.get(settings.whatsapp_web_url)
                is_logged_in = check_session_health(driver, timeout=10)
                if is_logged_in:
                    st.success("✅ WhatsApp Web session is ACTIVE and logged in!")
                else:
                    st.warning("⚠️ Session not logged in. Please scan the QR code in the opened browser window.")
            except Exception as e:
                st.error(f"Health Check Error: {e!s}")
            finally:
                if driver:
                    close_driver(driver)
