"""Reconciliation recall on injected errors."""

import pandas as pd
from reconciliation import reconcile


def test_status_counts_present(recon):
    counts = recon["status"].value_counts().to_dict()
    assert counts.get("MATCHED", 0) > 1000
    assert counts.get("MISSING_PAYMENT", 0) > 0
    assert counts.get("DUPLICATE", 0) > 0


def test_missing_bank_detected(raw, recon):
    pay = raw["payments"]
    inj_ids = pay[pay["injected_error"] == "missing_bank"]["invoice_id"].tolist()
    assert inj_ids, "no injected missing-bank payments"
    inv_status = dict(zip(recon["invoice_id"], recon["status"], strict=True))
    assert all(inv_status.get(i) == "MISSING_BANK_TRANSACTION" for i in inj_ids)


def test_missing_bank_priority_beats_partial():
    """MISSING_BANK_TRANSACTION outranks PARTIAL_PAYMENT."""
    inv = pd.DataFrame(
        [
            {
                "invoice_id": "INV1",
                "vendor_id": "V1",
                "total_amount": 1000.0,
                "currency": "INR",
            }
        ]
    )
    # partial payment whose bank reference does not exist
    pay = pd.DataFrame(
        [
            {
                "invoice_id": "INV1",
                "payment_id": "PAY1",
                "amount": 700.0,
                "currency": "INR",
                "bank_reference": "NOPE",
            }
        ]
    )
    bank = pd.DataFrame(
        [
            {
                "reference": "OTHER",
                "transaction_type": "Debit",
                "counterparty": "x",
                "amount": -1,
            }
        ]
    )
    vendors = pd.DataFrame([{"vendor_id": "V1", "vendor_name": "Vend"}])
    res = reconcile(inv, pay, bank, vendors)
    assert res.iloc[0]["status"] == "MISSING_BANK_TRANSACTION"


def test_duplicate_invoice_detected(raw, recon):
    inj = raw["vendor_invoices"]
    inj_ids = inj[inj["injected_error"] == "duplicate_invoice"]["invoice_id"].tolist()
    assert inj_ids, "no injected duplicates"
    detected = set(recon[recon["status"] == "DUPLICATE"]["invoice_id"])
    assert set(inj_ids).issubset(detected)


def test_amount_mismatch_detected(raw, recon):
    inj = raw["payments"]
    inj_ids = inj[inj["injected_error"] == "amount_mismatch"]["invoice_id"].tolist()
    assert inj_ids
    inv_status = dict(zip(recon["invoice_id"], recon["status"], strict=True))
    assert all(inv_status.get(i) == "AMOUNT_MISMATCH" for i in inj_ids)


def test_currency_mismatch_detected(raw, recon):
    inj = raw["payments"]
    inj_ids = inj[inj["injected_error"] == "currency_mismatch"]["invoice_id"].tolist()
    assert inj_ids
    inv_status = dict(zip(recon["invoice_id"], recon["status"], strict=True))
    assert all(inv_status.get(i) == "CURRENCY_MISMATCH" for i in inj_ids)


def test_status_identity(recon):
    # every invoice has exactly one status
    assert recon["invoice_id"].is_unique
    assert recon["status"].notna().all()
