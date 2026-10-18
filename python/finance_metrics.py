"""Finance metrics: payables, receivables, aging, payment performance.

Reported in both raw amounts (as recorded) and INR (FX-converted via
daily fx_rates), matching the API /metrics and the SQL reference queries.
"""

from __future__ import annotations

import config as C
import pandas as pd


def _fx_rate(df, fx):
    """Per-row FX rate to INR, joined on (currency, invoice_date).

    Mirrors the SQL view logic, falling back to 1.0 (the INR base
    rate) when no rate exists for that date.
    """
    if fx is None or fx.empty:
        return pd.Series(1.0, index=df.index).to_numpy()
    f = fx[fx["to_currency"] == "INR"][["rate_date", "from_currency", "rate"]]
    f = f.assign(rate_date=pd.to_datetime(f["rate_date"]).dt.date)
    f = f.rename(columns={"rate_date": "_date", "from_currency": "_cur"})
    m = df.copy()
    m["_date"] = pd.to_datetime(m["invoice_date"]).dt.date
    merged = m[["currency", "_date"]].merge(
        f, left_on=["currency", "_date"], right_on=["_cur", "_date"], how="left"
    )
    return merged["rate"].fillna(1.0).astype(float).to_numpy()


def _to_inr(df, fx):
    """Convert a DataFrame's total_amount column to INR using fx_rates."""
    return df["total_amount"].astype(float).to_numpy() * _fx_rate(df, fx)


def compute(frames, recon=None, as_of=None):
    vi = frames["vendor_invoices"].copy()
    pay = frames["payments"].copy()
    cinv = frames["customer_invoices"].copy()
    fx = frames.get("fx_rates")
    today = pd.Timestamp(as_of or C.END_DATE)

    # Outstanding payable per invoice:
    #   MATCHED / AMOUNT_MISMATCH (overpaid) -> 0
    #   PARTIAL_PAYMENT                      -> total - paid (residual)
    #   other (unpaid, wrong currency or no
    #   bank confirmation)                   -> full invoice total
    vi["amount_owed"] = vi["total_amount"].astype(float)
    if recon is not None:
        status_map = recon.set_index("invoice_id")["status"]
        paid_map = pay.groupby("invoice_id")["amount"].first().astype(float)

        def _owed(row):
            st = status_map.get(row["invoice_id"])
            if st in ("MATCHED", "AMOUNT_MISMATCH"):
                return 0.0
            if st == "PARTIAL_PAYMENT":
                return max(
                    float(row["total_amount"])
                    - float(paid_map.get(row["invoice_id"], 0.0)),
                    0.0,
                )
            return float(row["total_amount"])

        vi["amount_owed"] = vi.apply(_owed, axis=1)
    outstanding = vi[vi["amount_owed"] > 0].copy()
    total_payables = float(outstanding["amount_owed"].sum())
    total_payables_inr = float(
        (outstanding["amount_owed"].to_numpy() * _fx_rate(outstanding, fx)).sum()
    )

    # aging buckets (vs due_date)
    outstanding = outstanding.copy()
    outstanding["due_date"] = pd.to_datetime(outstanding["due_date"])
    outstanding["days_overdue"] = (today - outstanding["due_date"]).dt.days
    buckets = {"1-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for d in outstanding["days_overdue"]:
        if d <= 0:
            continue
        elif d <= 30:
            buckets["1-30"] += 1
        elif d <= 60:
            buckets["31-60"] += 1
        elif d <= 90:
            buckets["61-90"] += 1
        else:
            buckets["90+"] += 1

    # receivables (unpaid customer invoices)
    unpaid = cinv[cinv["status"] != "Paid"].copy()
    total_receivables = float(unpaid["total_amount"].sum())
    total_receivables_inr = float(_to_inr(unpaid, fx).sum())

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
        "total_payables_inr": total_payables_inr,
        "total_receivables": total_receivables,
        "total_receivables_inr": total_receivables_inr,
        "outstanding_invoices": len(outstanding),
        "aging_buckets": buckets,
        "on_time_payment_pct": round(float(on_time), 2),
        "avg_payment_delay_days": round(avg_delay, 2),
    }
    return metrics, outstanding


def main():
    from reconciliation import load_frames as rl
    from reconciliation import reconcile
    from validation import load_frames

    frames = load_frames()
    rf = rl()
    recon = reconcile(rf["invoices"], rf["payments"], rf["bank"], rf["vendors"])
    metrics, _ = compute(frames, recon)
    print("Finance metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
