"""Orchestrates the full analytics pipeline and writes processed CSVs.

Run:
    python python/report_exporter.py
"""

from __future__ import annotations

import config as C
import pandas as pd
from anomaly_detection import detect
from finance_metrics import compute
from inventory_analysis import analyze
from reconciliation import load_frames as rload
from reconciliation import reconcile
from validation import load_frames as vload
from validation import run_controls


def main():
    print("Reconciliation ...")
    rf = rload()
    recon = reconcile(rf["invoices"], rf["payments"], rf["bank"], rf["vendors"])
    recon.to_csv(C.PROCESSED_DIR / "reconciliation_report.csv", index=False)

    print("Controls ...")
    vf = vload()
    controls = run_controls(vf)
    controls.to_csv(C.PROCESSED_DIR / "controls_report.csv", index=False)

    print("Anomalies ...")
    anomalies = detect(vf)
    anomalies.to_csv(C.PROCESSED_DIR / "anomaly_report.csv", index=False)

    print("Inventory ...")
    _inv, util, low, over, inv_summary = analyze(vf)
    low.to_csv(C.PROCESSED_DIR / "inventory_low_stock.csv", index=False)
    over.to_csv(C.PROCESSED_DIR / "inventory_overstock.csv", index=False)
    util.to_csv(C.PROCESSED_DIR / "warehouse_utilization.csv", index=False)

    print("Finance metrics ...")
    metrics, _ = compute(vf, recon)
    pd.DataFrame([metrics]).to_csv(C.PROCESSED_DIR / "finance_metrics.csv", index=False)

    print("\n=== SUMMARY ===")
    print("Reconciliation:", recon["status"].value_counts().to_dict())
    print("Controls by rule:", controls["rule_id"].value_counts().to_dict())
    print("Anomalies:", len(anomalies))
    print(f"Inventory value: {inv_summary['total_inventory_value']:.2f}")
    print("Metrics:", metrics)


if __name__ == "__main__":
    main()
