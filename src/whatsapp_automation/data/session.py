from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from ..config.settings import settings

engine = create_engine(settings.db_url, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def get_session():
    return SessionLocal()
