import sys
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "backend"))

import config as C  # noqa: E402
from reconciliation import load_frames as rload, reconcile  # noqa: E402
from validation import load_frames as vload, run_controls  # noqa: E402
from anomaly_detection import detect  # noqa: E402


@pytest.fixture(scope="session")
def raw():
    return {k: pd.read_csv(C.RAW_DIR / f"{k}.csv") for k in [
        "vendor_invoices", "payments", "bank_transactions", "inventory",
        "customer_invoices", "vendors", "warehouses",
    ]}


@pytest.fixture(scope="session")
def recon(raw):
    rf = rload()
    return reconcile(rf["invoices"], rf["payments"], rf["bank"], rf["vendors"])


@pytest.fixture(scope="session")
def controls(raw):
    vf = vload()
    return run_controls(vf)


@pytest.fixture(scope="session")
def anomalies(raw):
    vf = vload()
    return detect(vf)
