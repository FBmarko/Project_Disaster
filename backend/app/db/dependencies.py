from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session per request and ensure safe closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
