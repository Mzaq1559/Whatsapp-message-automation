from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    whatsapp_web_url: str = Field(..., env='WHATSAPP_WEB_URL')
    db_url: str = Field(..., env='DB_URL')
    scheduler_timezone: str = Field('UTC', env='APScheduler_TIMEZONE')

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

settings = Settings()
