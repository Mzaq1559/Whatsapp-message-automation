from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SAFETY_MODE_PRESETS: dict[str, dict[str, Any]] = {
    "Conservative": {
        "min_send_delay": 10.0,
        "max_jitter": 5.0,
        "max_sends_per_run": 25,
        "max_sends_per_24h": 50,
    },
    "Standard": {
        "min_send_delay": 5.0,
        "max_jitter": 3.0,
        "max_sends_per_run": 50,
        "max_sends_per_24h": 100,
    },
}

class Settings(BaseSettings):
    whatsapp_web_url: str = Field(default="https://web.whatsapp.com", alias="WHATSAPP_WEB_URL")
    db_url: str = Field(default="sqlite:///whatsapp_automation.db", alias="DB_URL")
    chrome_profile_dir: str = Field(
        default_factory=lambda: str(Path.home() / ".whatsapp_automation_chrome_profile"),
        alias="CHROME_PROFILE_DIR",
    )
    headless: bool = Field(default=False, alias="HEADLESS")
    min_send_delay: float = Field(default=5.0, alias="MIN_SEND_DELAY")
    max_jitter: float = Field(default=3.0, alias="MAX_JITTER")
    max_sends_per_run: int = Field(default=50, alias="MAX_SENDS_PER_RUN")
    max_sends_per_24h: int = Field(default=100, alias="MAX_SENDS_PER_24H")
    safety_mode: str = Field(default="Conservative", alias="SAFETY_MODE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="whatsapp_automation.log", alias="LOG_FILE")
    scheduler_timezone: str = Field(default="UTC", alias="SCHEDULER_TIMEZONE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def apply_safety_preset(self, preset_name: str) -> None:
        if preset_name in SAFETY_MODE_PRESETS:
            preset = SAFETY_MODE_PRESETS[preset_name]
            self.safety_mode = preset_name
            self.min_send_delay = preset["min_send_delay"]
            self.max_jitter = preset["max_jitter"]
            self.max_sends_per_run = preset["max_sends_per_run"]
            self.max_sends_per_24h = preset["max_sends_per_24h"]

settings = Settings()
# Apply initial preset default if specified
if settings.safety_mode in SAFETY_MODE_PRESETS:
    settings.apply_safety_preset(settings.safety_mode)
