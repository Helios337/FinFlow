"""Metrics, anomaly and AI guardrail tests."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from finance_metrics import compute  # noqa: E402
from reconciliation import load_frames as rload  # noqa: E402
from reconciliation import reconcile  # noqa: E402
from validation import load_frames as vload  # noqa: E402

from backend.ai.copilot import validate_sql  # noqa: E402


def test_metrics_sane(raw):
    rf = rload()
    recon = reconcile(rf["invoices"], rf["payments"], rf["bank"], rf["vendors"])
    vf = vload()
    metrics, _ = compute(vf, recon)
    assert metrics["total_payables"] > 0
    assert 0 <= metrics["on_time_payment_pct"] <= 100
    assert metrics["aging_buckets"]["90+"] >= 0


def test_guardrail_blocks_non_select():
    assert validate_sql("DELETE FROM vendors")[0] is False
    assert validate_sql("INSERT INTO payments VALUES (1)")[0] is False
    assert validate_sql("SELECT * FROM secret_table")[0] is False
    ok, _ = validate_sql("SELECT vendor_id FROM vendors")
    assert ok is True


def test_guardrail_allows_joins():
    ok, err = validate_sql(
        "SELECT v.vendor_id FROM vendors v JOIN payments p ON p.invoice_id=v.vendor_id"
    )
    assert ok, err


def test_guardrail_blocks_statement_less_select():
    """SELECTs that call functions without a table (e.g. pg_sleep) are blocked."""
    assert validate_sql("SELECT pg_sleep(10)")[0] is False
    assert validate_sql("SELECT NOW()")[0] is False
    assert validate_sql("SELECT 1")[0] is False


def test_metrics_include_inr_values(raw):
    rf = rload()
    recon = reconcile(rf["invoices"], rf["payments"], rf["bank"], rf["vendors"])
    vf = vload()
    metrics, _ = compute(vf, recon)
    assert "total_payables_inr" in metrics
    assert "total_receivables_inr" in metrics
    assert metrics["total_payables_inr"] > 0
    assert metrics["total_receivables_inr"] > 0
