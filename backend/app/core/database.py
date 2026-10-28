from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None
if settings.database_url:
    # Supabase connection strings may use postgres://; SQLAlchemy expects postgresql://.
    database_url = settings.database_url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database is not configured. Set DATABASE_URL in .env.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
