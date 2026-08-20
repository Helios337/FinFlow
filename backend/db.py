"""FastAPI backend — database layer."""
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
import config as C  # noqa: E402

engine = create_engine(C.DB_URL, pool_pre_ping=True, future=True)


def fetch_all(sql, params=None):
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text(sql), params or {}).mappings().all()]


def fetch_one(sql, params=None):
    with engine.connect() as conn:
        r = conn.execute(text(sql), params or {}).mappings().first()
        return dict(r) if r else None
