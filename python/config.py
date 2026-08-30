"""Central configuration for FinanceOps360."""
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLE_DIR = DATA_DIR / "sample"

for _d in (RAW_DIR, PROCESSED_DIR, SAMPLE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Determinism
SEED = int(os.getenv("FO360_SEED", "42"))

# Reporting / base currency
BASE_CURRENCY = "INR"

# Currencies used in the simulation (non-base -> base rate is generated)
CURRENCIES = ["INR", "USD", "EUR", "AED", "SGD"]

# Dataset volumes
VOLUMES = {
    "vendors": 300,
    "customers": 500,
    "products": 100,
    "warehouses": 8,
    "employees": 50,
    "purchase_orders": 5000,
    "vendor_invoices": 7000,
    "payments": 6000,
    "bank_transactions": 12000,
    "customer_invoices": 5000,
    "inventory_movements": 15000,
    "inventory_snapshots": 20000,
    "expenses": 3000,
}

# Error injection rates (fraction of relevant population)
ERROR_RATES = {
    "duplicate_invoice": 0.008,
    "missing_payment": 0.015,
    "amount_mismatch": 0.020,
    "duplicate_bank": 0.005,
    "currency_mismatch": 0.007,
    "timing_diff": 0.010,
    "wrong_vendor_mapping": 0.005,
    "inventory_mismatch": 0.010,
    "unusual_txn": 0.006,
}

# Business date window
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
INVENTORY_MONTHS = ["2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01", "2024-12-01"]

# Tolerance for amount matching
AMOUNT_TOLERANCE = 0.005  # 0.5%
DATE_WINDOW_DAYS = 5

DB_URL = (
    f"postgresql+psycopg://{os.getenv('POSTGRES_USER','financeops')}"
    f":{os.getenv('POSTGRES_PASSWORD','financeops')}"
    f"@{os.getenv('POSTGRES_HOST','localhost')}"
    f":{os.getenv('POSTGRES_PORT','5433')}"
    f"/{os.getenv('POSTGRES_DB','financeops')}"
)
