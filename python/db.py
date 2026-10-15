"""Database engine helpers."""

from pathlib import Path

import config as C
from sqlalchemy import create_engine, text

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(C.DB_URL, future=True, pool_pre_ping=True)
    return _engine


def _split_statements(sql):
    """Split a SQL script on statement-terminating semicolons.

    Semicolons inside single-quoted strings or ``$$...$$`` dollar-quoted
    blocks (e.g. DO blocks) are preserved, so multi-statement scripts with
    function bodies or DO blocks execute correctly.
    """
    statements = []
    current = []
    in_squote = False
    in_dollar = False
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if in_dollar:
            current.append(ch)
            if ch == "$" and i + 1 < n and sql[i + 1] == "$":
                current.append("$")
                i += 2
                in_dollar = False
                continue
        elif in_squote:
            current.append(ch)
            if ch == "'":
                if i + 1 < n and sql[i + 1] == "'":
                    current.append("'")
                    i += 2
                    continue
                in_squote = False
        else:
            if ch == "'":
                in_squote = True
                current.append(ch)
            elif ch == "$" and i + 1 < n and sql[i + 1] == "$":
                in_dollar = True
                current.append("$$")
                i += 2
                continue
            elif ch == ";":
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
                i += 1
                continue
            else:
                current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def execute_sql_file(path):
    """Run a .sql file (statement separator: semicolon). Strips comments."""
    import re

    engine = get_engine()
    sql = Path(path).read_text()
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)  # block comments
    sql = re.sub(r"--[^\n]*", "", sql)  # line comments
    with engine.begin() as conn:
        for stmt in _split_statements(sql):
            if stmt:
                conn.execute(text(stmt))
