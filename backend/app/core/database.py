import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.get_database_url()
        connect_args = {}
        if db_url.startswith("postgresql"):
            connect_args["connect_timeout"] = 3

        engine_candidate = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args,
        )

        # Probe database connectivity
        try:
            with engine_candidate.connect() as conn:
                conn.execute(text("SELECT 1"))
            _engine = engine_candidate
        except Exception as exc:
            logger.warning(
                f"Primary database connection unavailable ({exc}). Using local SQLite fallback database."
            )
            local_engine = create_engine(
                "sqlite:///./commerce.db",
                connect_args={"check_same_thread": False},
            )
            # Ensure tables and seed exist
            import app.models  # noqa
            Base.metadata.create_all(local_engine)
            try:
                from app.core.seed import seed_catalog
                with Session(local_engine) as session:
                    seed_catalog(session)
            except Exception as seed_err:
                logger.warning(f"Local seed warning: {seed_err}")
            _engine = local_engine

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
    try:
        engine = get_engine()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            return result == 1
    except Exception:
        return False
