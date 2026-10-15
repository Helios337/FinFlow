"""Load raw CSVs into PostgreSQL.

Run order:
    python python/db_loader.py
"""

import config as C
import pandas as pd
from db import execute_sql_file, get_engine

TABLE_ORDER = [
    "fx_rates",
    "vendors",
    "customers",
    "warehouses",
    "products",
    "employees",
    "purchase_orders",
    "purchase_order_items",
    "vendor_invoices",
    "payments",
    "bank_transactions",
    "customer_invoices",
    "inventory",
    "inventory_movements",
    "expenses",
]


def main():
    print("Creating schema ...")
    execute_sql_file(C.BASE_DIR / "sql" / "schema.sql")

    engine = get_engine()
    # idempotent reload: clear existing rows (FK-safe)
    from sqlalchemy import text as _text

    with engine.begin() as conn:
        conn.execute(
            _text("TRUNCATE TABLE " + ", ".join(TABLE_ORDER) + " RESTART IDENTITY CASCADE")
        )
    for table in TABLE_ORDER:
        csv_path = C.RAW_DIR / f"{table}.csv"
        if not csv_path.exists():
            print(f"  SKIP {table} (no csv)")
            continue
        df = pd.read_csv(csv_path)
        # coerce date columns to python date objects (psycopg3 + multi INSERT)
        for col in df.columns:
            if "date" in col.lower():
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        # coerce NaN strings
        df = df.where(pd.notnull(df), None)
        print(f"Loading {table}: {len(df)} rows")
        df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=2000)
    print("Load complete.")


if __name__ == "__main__":
    main()
