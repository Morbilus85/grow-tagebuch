import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

DATA_DIR = Path(os.environ.get("GROW_DATA_DIR", "/data"))
PHOTO_DIR = DATA_DIR / "photos"
DB_PATH = DATA_DIR / "grow.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
PHOTO_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}
)


def init_db() -> None:
    from . import models  # noqa: F401  (registriert Tabellen)

    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")


def get_session():
    with Session(engine) as session:
        yield session
