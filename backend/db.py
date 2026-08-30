"""FastAPI backend - database layer."""
import sys
import datetime as _dt
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
import config as C  # noqa: E402

engine = create_engine(C.DB_URL, pool_pre_ping=True, future=True)


def _serialize(row):
    """Convert date/datetime values to ISO strings for Pydantic str fields."""
    return {k: (v.isoformat() if isinstance(v, (_dt.date, _dt.datetime)) else v)
            for k, v in row.items()}


def fetch_all(sql, params=None):
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
        return [_serialize(dict(r)) for r in rows]


def fetch_one(sql, params=None):
    with engine.connect() as conn:
        r = conn.execute(text(sql), params or {}).mappings().first()
        return _serialize(dict(r)) if r else None
