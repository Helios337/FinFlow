"""Finance metrics: payables, receivables, aging, payment performance."""
from __future__ import annotations
import pandas as pd
import numpy as np

import config as C


def compute(frames, recon=None, as_of=None):
    vi = frames["vendor_invoices"].copy()
    pay = frames["payments"].copy()
    cinv = frames["customer_invoices"].copy()
    today = pd.Timestamp(as_of or C.END_DATE)

    # outstanding payable = invoices not fully matched/paid
    paid_ids = set()
    if recon is not None:
        paid_ids = set(recon[recon["status"].isin(["MATCHED", "PARTIAL_PAYMENT"])]["invoice_id"])
    outstanding = vi[~vi["invoice_id"].isin(paid_ids)]
    total_payables = float(outstanding["total_amount"].sum())

    # aging buckets (vs due_date)
    outstanding = outstanding.copy()
    outstanding["due_date"] = pd.to_datetime(outstanding["due_date"])
    outstanding["days_overdue"] = (today - outstanding["due_date"]).dt.days
    buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for d in outstanding["days_overdue"]:
        if d <= 0:
            continue
        elif d <= 30:
            buckets["0-30"] += 1
        elif d <= 60:
            buckets["31-60"] += 1
        elif d <= 90:
            buckets["61-90"] += 1
        else:
            buckets["90+"] += 1

    # receivables
    cinv = cinv.copy()
    cinv["due_date"] = pd.to_datetime(cinv["due_date"])
    total_receivables = float(cinv[cinv["status"] != "Paid"]["total_amount"].sum())

    # payment performance
    pay = pay.copy()
    pay["payment_date"] = pd.to_datetime(pay["payment_date"])
    merged = pay.merge(vi[["invoice_id", "due_date"]], on="invoice_id", how="left")
    merged["due_date"] = pd.to_datetime(merged["due_date"])
    merged["delay"] = (merged["payment_date"] - merged["due_date"]).dt.days
    on_time = (merged["delay"] <= 0).mean() * 100
    avg_delay = float(merged["delay"].mean())

    metrics = {
        "total_payables": total_payables,
        "total_receivables": total_receivables,
        "outstanding_invoices": int(len(outstanding)),
        "aging_buckets": buckets,
        "on_time_payment_pct": round(float(on_time), 2),
        "avg_payment_delay_days": round(avg_delay, 2),
    }
    return metrics, outstanding


def date_today():
    return C.END_DATE


def main():
    from validation import load_frames
    from reconciliation import load_frames as rl, reconcile
    frames = load_frames()
    rf = rl()
    recon = reconcile(rf["invoices"], rf["payments"], rf["bank"], rf["vendors"])
    metrics, _ = compute(frames, recon)
    print("Finance metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
