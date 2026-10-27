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
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        _add_missing_columns(conn)


def _add_missing_columns(conn) -> None:
    """Leichte Migration: neue, optionale Spalten an bestehende Tabellen anhängen."""
    for table in SQLModel.metadata.sorted_tables:
        existing = {r[1] for r in conn.exec_driver_sql(f'PRAGMA table_info("{table.name}")')}
        for col in table.columns:
            if col.name in existing:
                continue
            ddl_type = col.type.compile(dialect=engine.dialect)
            default = ""
            if col.default is not None and getattr(col.default, "is_scalar", False):
                v = col.default.arg
                default = f" DEFAULT {int(v) if isinstance(v, bool) else repr(v)}"
            conn.exec_driver_sql(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {ddl_type}{default}')


def get_session():
    with Session(engine) as session:
        yield session
