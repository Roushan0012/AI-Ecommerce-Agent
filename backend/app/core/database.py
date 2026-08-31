from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.get_database_url()
        _engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return _engine


def get_db() -> Generator[Session, None, None]:
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """Probe the database connection with a lightweight test query."""
    engine = get_engine()
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar()
        return result == 1
