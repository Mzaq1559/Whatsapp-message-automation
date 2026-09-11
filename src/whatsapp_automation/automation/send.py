import time
from typing import Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy.orm import Session

from ..config.settings import SAFETY_MODE_PRESETS, settings
from ..core.jobs import get_job, validate_job
from ..core.templates import render_template, utc_now
from ..data.models import SendLog
from .driver import check_session_health, close_driver, init_driver
from .retry import (
    ContactNotFoundError,
    SendFailedError,
    human_delay,
    retry_on_selenium_error,
)


class WhatsAppPage:
    """Page Object Encapsulating WhatsApp Web DOM Interactions."""

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    def open(self) -> None:
        if "web.whatsapp.com" not in self.driver.current_url:
            self.driver.get(settings.whatsapp_web_url)
        if not check_session_health(self.driver, timeout=15):
            raise SendFailedError("WhatsApp Web session is not logged in. Please scan QR code first.")

    @retry_on_selenium_error(max_attempts=3)
    def search_and_select_contact(self, contact_ref: str) -> None:
        """
        Searches for a contact or group by display name or phone number.
        Raises ContactNotFoundError if no matching chat is found.
        """
        # Find search box
        search_xpath = (
            "//div[@contenteditable='true'][@data-tab='3'] | "
            "//div[@contenteditable='true'][contains(@aria-label, 'Search')]"
        )
        search_box = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, search_xpath))
        )
        search_box.click()

        # Clear existing text in search box
        search_box.send_keys(Keys.CONTROL + "a")
        search_box.send_keys(Keys.BACKSPACE)
        time.sleep(0.5)

        # Type contact reference
        search_box.send_keys(contact_ref)
        time.sleep(1.5)

        # Check for 'No chat, contacts, or messages found' or empty result list
        no_result_xpath = (
            "//div[contains(text(), 'No chats, contacts or messages found')] | "
            "//div[contains(text(), 'No results found')]"
        )
        no_results = self.driver.find_elements(By.XPATH, no_result_xpath)
        if no_results and any(nr.is_displayed() for nr in no_results):
            raise ContactNotFoundError(f"Contact/Group '{contact_ref}' not found on WhatsApp.")

        # Find first matching chat in search results list
        result_chat_xpath = (
            "//div[@id='pane-side']//div[contains(@role, 'listitem')] | "
            "//div[@id='pane-side']//div[contains(@class, '_ak8l')]"
        )
        try:
            chat_element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, result_chat_xpath))
            )
            chat_element.click()
            time.sleep(1.0)
        except Exception as exc:
            raise ContactNotFoundError(f"Failed to select contact '{contact_ref}': {exc!s}") from exc

    @retry_on_selenium_error(max_attempts=3)
    def send_message(self, message_text: str) -> None:
        """
        Types and sends a message in the currently open chat.
        Handles multiline text and special characters.
        """
        # Message input box selector
        msg_box_xpath = (
            "//footer//div[@contenteditable='true'][@data-tab='10'] | "
            "//footer//div[@contenteditable='true'][contains(@aria-label, 'Type a message')]"
        )
        msg_box = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, msg_box_xpath))
        )
        msg_box.click()

        # Input multiline text using Shift+Enter for linebreaks
        lines = message_text.split("\n")
        for idx, line in enumerate(lines):
            if line:
                msg_box.send_keys(line)
            if idx < len(lines) - 1:
                msg_box.send_keys(Keys.SHIFT + Keys.ENTER)

        time.sleep(0.5)

        # Click send button or press enter
        send_btn_xpath = "//button[@aria-label='Send'] | //span[@data-icon='send']/parent::button"
        send_buttons = self.driver.find_elements(By.XPATH, send_btn_xpath)

        if send_buttons and send_buttons[0].is_displayed():
            send_buttons[0].click()
        else:
            msg_box.send_keys(Keys.ENTER)

        # Brief delay to allow message dispatch DOM update
        time.sleep(1.0)

def execute_live_job(
    db: Session,
    job_id: int,
    driver: webdriver.Chrome | None = None,
    user_data_dir: str | None = None,
    headless: bool = False,
) -> dict[str, Any]:
    """
    Executes a live WhatsApp job using Selenium automation.
    Reuses provided driver or spawns a long-lived Chrome instance.
    """
    job = get_job(db, job_id)
    if not job:
        raise ValueError(f"Job ID {job_id} not found.")

    valid, errors = validate_job(db, job_id)
    if not valid:
        raise ValueError(f"Job validation failed: {'; '.join(errors)}")

    job.status = "running"
    db.commit()

    preset = SAFETY_MODE_PRESETS.get(
        job.safety_mode,
        {
            "min_send_delay": settings.min_send_delay,
            "max_jitter": settings.max_jitter,
        },
    )

    should_close_driver = False
    if driver is None:
        driver = init_driver(user_data_dir=user_data_dir, headless=headless)
        should_close_driver = True

    try:
        page = WhatsAppPage(driver)
        page.open()

        body = job.template_snapshot_body or (job.template.body if job.template else "")
        sent_count = 0
        failed_count = 0

        for recipient in job.recipients:
            if recipient.status not in ("pending", "failed"):
                continue

            contact = recipient.contact
            ref = contact.whatsapp_ref if contact else ""
            if not ref:
                log = SendLog(
                    job_recipient_id=recipient.id,
                    timestamp=utc_now(),
                    rendered_text="",
                    outcome="failure",
                    error="Contact has no whatsapp_ref.",
                    retry_count=0,
                )
                db.add(log)
                recipient.status = "failed"
                failed_count += 1
                continue

            try:
                rendered = render_template(
                    template_body=body,
                    recipient_vars=recipient.variables,
                    contact=contact,
                )

                # Search contact
                page.search_and_select_contact(ref)

                # Send message
                page.send_message(rendered)

                log = SendLog(
                    job_recipient_id=recipient.id,
                    timestamp=utc_now(),
                    rendered_text=rendered,
                    outcome="success",
                    error=None,
                    retry_count=0,
                )
                db.add(log)
                recipient.status = "success"
                sent_count += 1

                db.commit()

                # Human pacing delay between sends
                human_delay(
                    min_delay=preset.get("min_send_delay", 5.0),
                    max_jitter=preset.get("max_jitter", 3.0),
                )

            except ContactNotFoundError as cnf:
                log = SendLog(
                    job_recipient_id=recipient.id,
                    timestamp=utc_now(),
                    rendered_text="",
                    outcome="failure",
                    error=f"Contact Not Found: {cnf!s}",
                    retry_count=0,
                )
                db.add(log)
                recipient.status = "failed"
                failed_count += 1
                db.commit()

            except Exception as exc:
                log = SendLog(
                    job_recipient_id=recipient.id,
                    timestamp=utc_now(),
                    rendered_text="",
                    outcome="failure",
                    error=f"Send Error: {exc!s}",
                    retry_count=1,
                )
                db.add(log)
                recipient.status = "failed"
                failed_count += 1
                db.commit()

        if failed_count == 0:
            job.status = "completed"
        elif sent_count > 0:
            job.status = "completed_with_errors"
        else:
            job.status = "failed"

        db.commit()

        return {
            "job_id": job.id,
            "status": job.status,
            "total_recipients": len(job.recipients),
            "sent_count": sent_count,
            "failed_count": failed_count,
        }

    finally:
        if should_close_driver:
            close_driver(driver)
