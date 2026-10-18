"""Reconciliation engine: Invoice -> Payment -> Bank.

Implements the strict status priority (mutually exclusive):
  DUPLICATE > CURRENCY_MISMATCH > AMOUNT_MISMATCH > MISSING_BANK_TRANSACTION
  > PARTIAL_PAYMENT > MATCHED   (and MISSING_PAYMENT when no payment exists)

Reads from CSVs (or DataFrames) and writes reconciliation_results.
"""

from __future__ import annotations

import difflib

import config as C
import pandas as pd


def load_frames():
    raw = C.RAW_DIR
    return {
        "invoices": pd.read_csv(raw / "vendor_invoices.csv"),
        "payments": pd.read_csv(raw / "payments.csv"),
        "bank": pd.read_csv(raw / "bank_transactions.csv"),
        "vendors": pd.read_csv(raw / "vendors.csv"),
    }


def _amount_diff(inv_total, pay_amount):
    return round(float(pay_amount) - float(inv_total), 2)


def reconcile(invoices, payments, bank, vendors=None):
    results = []
    pay_by_inv = payments.groupby("invoice_id")
    bank_by_ref = bank.groupby("reference")

    # duplicate invoice detection (same vendor + amount + date window)
    inv_dup = invoices.copy()
    inv_dup["key"] = inv_dup["vendor_id"].astype(str) + "|" + inv_dup["total_amount"].astype(str)
    dup_keys = set(inv_dup["key"][inv_dup.duplicated(subset=["key"], keep=False)])

    for _, inv in invoices.iterrows():
        iid = inv["invoice_id"]
        inv_total = float(inv["total_amount"])
        cur = str(inv["currency"])

        # DUPLICATE (cloned id with -D, or identical vendor+amount)
        if str(iid).endswith("-D") or (f"{inv['vendor_id']}|{inv_total}" in dup_keys):
            results.append(
                _row(
                    iid,
                    None,
                    None,
                    "DUPLICATE",
                    1.0,
                    None,
                    False,
                    "Duplicate invoice detected (same vendor + amount).",
                )
            )
            continue

        if iid not in pay_by_inv.groups:
            results.append(
                _row(
                    iid,
                    None,
                    None,
                    "MISSING_PAYMENT",
                    1.0,
                    None,
                    None,
                    "Invoice has no linked payment record.",
                )
            )
            continue

        pay = pay_by_inv.get_group(iid).iloc[0]
        pid = pay["payment_id"]
        ref = pay["bank_reference"]
        pay_cur = str(pay["currency"])
        conf = 1.0
        notes = []

        if pay_cur != cur:
            results.append(
                _row(
                    iid,
                    pid,
                    ref,
                    "CURRENCY_MISMATCH",
                    conf,
                    _amount_diff(inv_total, float(pay["amount"])),
                    False,
                    f"Invoice {cur} vs payment {pay_cur}.",
                )
            )
            continue

        diff = _amount_diff(inv_total, float(pay["amount"]))
        tol = max(C.AMOUNT_TOLERANCE * inv_total, 0.01)
        if float(pay["amount"]) > inv_total + tol:
            results.append(
                _row(
                    iid,
                    pid,
                    ref,
                    "AMOUNT_MISMATCH",
                    conf,
                    diff,
                    True,
                    f"Overpayment: paid {diff} more than invoice total.",
                )
            )
            continue

        # bank match by reference (debit side). Checked BEFORE the
        # partial-payment check to honor the documented status priority:
        # MISSING_BANK_TRANSACTION > PARTIAL_PAYMENT.
        bank_match = None
        if ref in bank_by_ref.groups:
            cands = bank_by_ref.get_group(ref)
            cands = cands[cands["transaction_type"].isin(["Debit", "Transfer"])]
            if len(cands):
                bank_match = cands.iloc[0]

        if bank_match is None:
            results.append(
                _row(
                    iid,
                    pid,
                    ref,
                    "MISSING_BANK_TRANSACTION",
                    conf,
                    diff,
                    True,
                    "Payment has no matching bank transaction by reference.",
                )
            )
            continue

        if float(pay["amount"]) < inv_total - tol:
            results.append(
                _row(
                    iid,
                    pid,
                    ref,
                    "PARTIAL_PAYMENT",
                    conf,
                    diff,
                    True,
                    f"Partial/under payment: {diff} short of invoice total.",
                )
            )
            continue

        # counterparty sanity (soft review flag, not a hard status change)
        if vendors is not None:
            vname = vendors[vendors["vendor_id"] == inv["vendor_id"]]["vendor_name"]
            vname = vname.iloc[0] if len(vname) else ""
            cp = str(bank_match["counterparty"])
            if vname and difflib.SequenceMatcher(None, vname.lower(), cp.lower()).ratio() < 0.6:
                notes.append(f"Bank counterparty '{cp}' does not match vendor '{vname}'.")

        results.append(_row(iid, pid, ref, "MATCHED", conf, diff, True, " ".join(notes)))

    return pd.DataFrame(results)


def _row(
    invoice_id, payment_id, bank_reference, status, confidence, amount_diff, currency_match, notes
):
    return {
        "invoice_id": invoice_id,
        "payment_id": payment_id,
        "bank_reference": bank_reference,
        "status": status,
        "confidence": confidence,
        "amount_diff": amount_diff,
        "currency_match": currency_match,
        "notes": notes,
    }


def main():
    frames = load_frames()
    res = reconcile(frames["invoices"], frames["payments"], frames["bank"], frames["vendors"])
    out = C.PROCESSED_DIR / "reconciliation_report.csv"
    res.to_csv(out, index=False)
    print(f"Wrote {out}: {len(res)} rows")
    print("\nStatus breakdown:")
    print(res["status"].value_counts().to_string())


if __name__ == "__main__":
    main()
