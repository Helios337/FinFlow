"""Data-access services backed by PostgreSQL."""

from __future__ import annotations

from . import db

LIMIT = 200

# Outstanding payable amount (INR) for a vendor invoice, given its
# reconciliation status. MATCHED / overpaid (AMOUNT_MISMATCH) -> 0;
# PARTIAL_PAYMENT -> residual balance (total - paid, FX-converted);
# everything else (unpaid, wrong currency or no bank confirmation)
# -> full invoice total. Matches python/finance_metrics.py and
# sql/finance_metrics.sql.
AP_OUTSTANDING_SQL = (
    "COALESCE(CASE WHEN r.status IN ('MATCHED','AMOUNT_MISMATCH') THEN 0 "
    "WHEN r.status = 'PARTIAL_PAYMENT' THEN GREATEST("
    "vi.total_inr - COALESCE(p.amount, 0) * "
    "(vi.total_inr / NULLIF(vi.total_amount, 0)), 0) "
    "ELSE vi.total_inr END, 0)"
)
AP_JOIN_SQL = (
    "v_vendor_invoices_inr vi "
    "LEFT JOIN reconciliation_results r ON r.invoice_id = vi.invoice_id "
    "LEFT JOIN (SELECT invoice_id, SUM(amount) AS amount FROM payments "
    "GROUP BY invoice_id) p ON p.invoice_id = vi.invoice_id"
)


def get_vendors(limit=LIMIT):
    return db.fetch_all("SELECT * FROM vendors ORDER BY vendor_id LIMIT :l", {"l": limit})


def get_invoices(status=None, limit=LIMIT):
    if status:
        return db.fetch_all(
            "SELECT * FROM vendor_invoices WHERE status=:s ORDER BY invoice_id LIMIT :l",
            {"s": status, "l": limit},
        )
    return db.fetch_all("SELECT * FROM vendor_invoices ORDER BY invoice_id LIMIT :l", {"l": limit})


def get_payments(limit=LIMIT):
    return db.fetch_all("SELECT * FROM payments ORDER BY payment_id LIMIT :l", {"l": limit})


def get_transactions(limit=LIMIT):
    return db.fetch_all(
        "SELECT transaction_id, transaction_date, transaction_type, amount, currency, counterparty "
        "FROM bank_transactions ORDER BY transaction_id LIMIT :l",
        {"l": limit},
    )


def get_inventory(limit=LIMIT):
    return db.fetch_all("SELECT * FROM inventory ORDER BY warehouse_id LIMIT :l", {"l": limit})


def get_reconciliation(status=None, limit=LIMIT):
    if status:
        return db.fetch_all(
            "SELECT * FROM reconciliation_results WHERE status=:s ORDER BY invoice_id LIMIT :l",
            {"s": status, "l": limit},
        )
    return db.fetch_all(
        "SELECT * FROM reconciliation_results ORDER BY invoice_id LIMIT :l", {"l": limit}
    )


def get_anomalies(severity=None, limit=LIMIT):
    if severity:
        return db.fetch_all(
            "SELECT * FROM anomalies WHERE severity=:s ORDER BY score DESC LIMIT :l",
            {"s": severity, "l": limit},
        )
    return db.fetch_all("SELECT * FROM anomalies ORDER BY score DESC LIMIT :l", {"l": limit})


def get_controls(limit=LIMIT):
    return db.fetch_all("SELECT * FROM controls_violations ORDER BY rule_id LIMIT :l", {"l": limit})


def get_metrics():
    payables = db.fetch_one(
        f"SELECT COALESCE(SUM({AP_OUTSTANDING_SQL}),0) AS v FROM {AP_JOIN_SQL}"
    )
    receivables = db.fetch_one(
        "SELECT COALESCE(SUM(total_amount * COALESCE(f.rate_to_inr,1)),0) AS v "
        "FROM customer_invoices ci "
        "LEFT JOIN v_fx_inr f ON f.from_currency = ci.currency AND f.rate_date = ci.invoice_date "
        "WHERE ci.status <> 'Paid'"
    )
    outstanding = db.fetch_one(
        f"SELECT COUNT(*) AS c FROM {AP_JOIN_SQL} WHERE {AP_OUTSTANDING_SQL} > 0"
    )
    rec = db.fetch_all("SELECT status, COUNT(*) AS c FROM reconciliation_results GROUP BY status")
    rec_map = {r["status"]: r["c"] for r in rec}
    anomalies = db.fetch_one("SELECT COUNT(*) AS c FROM anomalies")
    return {
        "total_payables_inr": float(payables["v"]) if payables else 0.0,
        "total_receivables_inr": float(receivables["v"]) if receivables else 0.0,
        "outstanding_invoices": int(outstanding["c"]) if outstanding else 0,
        "matched": rec_map.get("MATCHED", 0),
        "mismatched": rec_map.get("AMOUNT_MISMATCH", 0) + rec_map.get("CURRENCY_MISMATCH", 0),
        "duplicates": rec_map.get("DUPLICATE", 0),
        "anomalies": anomalies["c"] if anomalies else 0,
        "match_rate_pct": round(
            100.0 * rec_map.get("MATCHED", 0) / max(1, sum(rec_map.values())), 2
        ),
    }


# enable full-text style search helper used by AI
def execute_sql(sql):
    return db.fetch_all(sql)
