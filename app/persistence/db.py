from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# create engine for Postgres (sync)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,  # SQLAlchemy 1.4+ style
)

# Session factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session)

# helper for creating a session (used by UoW)
def create_session() -> Session:
    return SessionLocal()