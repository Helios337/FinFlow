"""Persist raw CSVs + analysis results into PostgreSQL.

Run order:
    python python/db_loader.py      # raw tables + schema
    python python/persist.py        # analysis result tables
"""
from __future__ import annotations
import pandas as pd

import config as C
from db import get_engine, execute_sql_file
from reconciliation import load_frames as rload, reconcile
from validation import load_frames as vload, run_controls
from anomaly_detection import detect


def _write(df, table, engine):
    df = df.where(pd.notnull(df), None)
    df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=2000)


def main():
    # ensure schema present
    execute_sql_file(C.BASE_DIR / "sql" / "schema.sql")
    execute_sql_file(C.BASE_DIR / "sql" / "views.sql")
    engine = get_engine()

    # truncate result tables for idempotent reload
    with engine.begin() as conn:
        for t in ["reconciliation_results", "anomalies", "controls_violations"]:
            conn.execute(__import__("sqlalchemy").text(f"TRUNCATE TABLE {t}"))

    print("Reconciliation -> reconciliation_results")
    rf = rload()
    recon = reconcile(rf["invoices"], rf["payments"], rf["bank"], rf["vendors"])
    _write(recon, "reconciliation_results", engine)

    print("Controls -> controls_violations")
    vf = vload()
    controls = run_controls(vf)
    _write(controls, "controls_violations", engine)

    print("Anomalies -> anomalies")
    anomalies = detect(vf)
    _write(anomalies, "anomalies", engine)

    print("Persist complete.")


if __name__ == "__main__":
    main()
