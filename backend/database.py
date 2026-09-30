"""SQLite connection shared by every request."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Load qa-tool/.env (one folder above backend/)
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# SQLite file. Default sits next to the project so the path is stable.
BASE_DIR = Path(__file__).resolve().parents[1]
default_db = (BASE_DIR / "qa.db").as_posix()
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db}")

# check_same_thread=False lets FastAPI use the connection across requests
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_connection, _connection_record):
    """SQLite ignores foreign keys unless this pragma is turned on."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_db():
    """Give each request its own session, then close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
