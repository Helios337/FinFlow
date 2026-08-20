"""Anomaly detection (explainable first).

Outputs a unified anomaly table:
  transaction_id, source_table, anomaly_type, score, severity,
  reason, expected_value, observed_value, recommended_action
"""
from __future__ import annotations
import pandas as pd
import numpy as np

import config as C


def _anom(tx_id, table, atype, score, severity, reason, expected, observed, action):
    return {
        "transaction_id": str(tx_id), "source_table": table, "anomaly_type": atype,
        "score": round(float(score), 4), "severity": severity, "reason": reason,
        "expected_value": round(float(expected), 2) if expected is not None else None,
        "observed_value": round(float(observed), 2) if observed is not None else None,
        "recommended_action": action,
    }


def detect(frames):
    anomalies = []

    # 1) Bank unusual transactions: z-score on debit magnitudes
    bank = frames["bank_transactions"].copy()
    debits = bank[bank["transaction_type"].isin(["Debit", "Transfer"])].copy()
    debits["mag"] = debits["amount"].abs()
    if len(debits) > 10:
        mu, sd = debits["mag"].mean(), debits["mag"].std() + 1e-9
        for _, r in debits.iterrows():
            z = (r["mag"] - mu) / sd
            if abs(z) > 3:
                sev = "HIGH" if abs(z) > 4 else "MEDIUM"
                anomalies.append(_anom(
                    r["transaction_id"], "bank_transactions", "unusual_amount",
                    abs(z), sev,
                    f"Transaction magnitude {abs(z):.1f} sigma from bank mean.",
                    mu, r["mag"], "Manual verification required."))

    # 2) Invoice amount IQR outliers
    vi = frames["vendor_invoices"]
    if len(vi) > 10:
        q1, q3 = vi["total_amount"].quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        for _, r in vi.iterrows():
            if r["total_amount"] > hi or r["total_amount"] < lo:
                sev = "MEDIUM"
                anomalies.append(_anom(
                    r["invoice_id"], "vendor_invoices", "invoice_amount_outlier",
                    abs(r["total_amount"] - (hi + lo) / 2) / (iqr + 1e-9), sev,
                    f"Invoice amount outside IQR band [{lo:.0f}, {hi:.0f}].",
                    (hi + lo) / 2, r["total_amount"], "Review invoice for legitimacy."))

    # 3) Vendor baseline: invoice >> vendor historical mean
    if len(vi) > 10:
        g = vi.groupby("vendor_id")["total_amount"]
        means, stds = g.mean(), g.std()
        for _, r in vi.iterrows():
            m, s = means.get(r["vendor_id"]), stds.get(r["vendor_id"])
            if m is None or s is None or pd.isna(s) or s == 0:
                continue
            if r["total_amount"] > m + 3 * s:
                ratio = r["total_amount"] / (m + 1e-9)
                sev = "HIGH" if ratio > 5 else "MEDIUM"
                anomalies.append(_anom(
                    r["invoice_id"], "vendor_invoices", "vendor_baseline_exceed",
                    ratio, sev,
                    f"{ratio:.1f}x vendor historical average.",
                    m, r["total_amount"], "Validate against PO and contract."))

    df = pd.DataFrame(anomalies)
    if len(df) == 0:
        df = pd.DataFrame(columns=["transaction_id", "source_table", "anomaly_type",
                                   "score", "severity", "reason", "expected_value",
                                   "observed_value", "recommended_action"])
    return df


def main():
    from validation import load_frames
    frames = load_frames()
    df = detect(frames)
    out = C.PROCESSED_DIR / "anomaly_report.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out}: {len(df)} anomalies")
    if len(df):
        print(df["anomaly_type"].value_counts().to_string())


if __name__ == "__main__":
    main()
