"""Database engine helpers."""
from pathlib import Path
from sqlalchemy import create_engine, text
import config as C

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(C.DB_URL, future=True, pool_pre_ping=True)
    return _engine


def execute_sql_file(path):
    """Run a .sql file (statement separator: semicolon). Strips comments."""
    import re
    engine = get_engine()
    sql = Path(path).read_text()
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)  # block comments
    sql = re.sub(r"--[^\n]*", "", sql)                    # line comments
    with engine.begin() as conn:
        for stmt in sql.split(";"):
            s = stmt.strip()
            if s:
                conn.execute(text(s))


def run_query(sql, params=None):
    from sqlalchemy import text
    with get_engine().connect() as conn:
        return conn.execute(text(sql), params or {}).mappings().all()
