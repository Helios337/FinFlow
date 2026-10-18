"""Build FinanceOps_Reconciliation.xlsx from processed + raw CSVs.

Run:
    python excel/build_workbook.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
import config as C

RED = PatternFill("solid", fgColor="FFC7CE")
GREEN = PatternFill("solid", fgColor="C6EFCE")
YELLOW = PatternFill("solid", fgColor="FFEB9C")
HDR = Font(bold=True, color="FFFFFF")
HDR_FILL = PatternFill("solid", fgColor="305496")


def _write_df(ws, df, start=1):
    cols = list(df.columns)
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=start, column=j, value=str(c))
        cell.font = HDR
        cell.fill = HDR_FILL
    for i, (_, row) in enumerate(df.iterrows(), start + 1):
        for j, c in enumerate(cols, 1):
            val = row[c]
            if pd.isna(val):
                val = None
            ws.cell(row=i, column=j, value=val)
    return len(df)


def _autosize(ws, max_w=40):
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        width = min(max_w, max((len(str(c.value)) for c in col if c.value is not None), default=10))
        ws.column_dimensions[letter].width = width + 2


def build():
    wb = Workbook()

    # ---- Dashboard ----
    dash = wb.active
    dash.title = "Dashboard"
    dash["A1"] = "FinanceOps360 - Reconciliation Dashboard"
    dash["A1"].font = Font(bold=True, size=14)
    raw = C.RAW_DIR
    proc = C.PROCESSED_DIR

    recon = pd.read_csv(proc / "reconciliation_report.csv")
    controls = pd.read_csv(proc / "controls_report.csv")
    anomalies = pd.read_csv(proc / "anomaly_report.csv")
    inv = pd.read_csv(raw / "inventory.csv")
    vi = pd.read_csv(raw / "vendor_invoices.csv")
    metrics = pd.read_csv(proc / "finance_metrics.csv").iloc[0]

    # True overdue: open (not fully matched) invoices past their
    # due date as of the dataset end. MISSING_PAYMENT alone is
    # NOT the same as overdue.
    matched_ids = set(recon[recon["status"] == "MATCHED"]["invoice_id"])
    open_vi = vi[~vi["invoice_id"].isin(matched_ids)].copy()
    open_vi["due_date"] = pd.to_datetime(open_vi["due_date"])
    asof = pd.Timestamp(C.END_DATE)
    overdue_cnt = int((open_vi["due_date"] < asof).sum())

    # Inventory value from the latest snapshot per (warehouse,
    # product): the inventory table holds several snapshot dates
    # per key, so summing all of them multi-counts the stock.
    inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"])
    latest_inv = (
        inv.sort_values("snapshot_date")
        .groupby(["warehouse_id", "product_id"])
        .tail(1)
    )
    inventory_value = float((latest_inv["quantity"] * latest_inv["unit_cost"]).sum())

    kpis = [
        (
            "Total Payables (INR, outstanding)",
            round(float(metrics["total_payables_inr"]), 2),
        ),
        (
            "Total Receivables (INR, outstanding)",
            round(float(metrics["total_receivables_inr"]), 2),
        ),
        ("Outstanding (Unmatched) Invoices", int((recon["status"] != "MATCHED").sum())),
        ("Overdue Invoices", overdue_cnt),
        ("Matched Transactions", int((recon["status"] == "MATCHED").sum())),
        ("Partial Payments", int((recon["status"] == "PARTIAL_PAYMENT").sum())),
        (
            "Mismatch Count",
            int(recon["status"].isin(["AMOUNT_MISMATCH", "CURRENCY_MISMATCH"]).sum()),
        ),
        ("Mismatch Value", round(recon["amount_diff"].abs().sum(), 2)),
        ("Inventory Value (INR, latest snapshot)", round(inventory_value, 2)),
        ("Control Violations", len(controls)),
        ("Anomalies", len(anomalies)),
    ]
    dash["A3"] = "KPI"
    dash["B3"] = "Value"
    dash["A3"].font = dash["B3"].font = Font(bold=True)
    for i, (k, v) in enumerate(kpis, 4):
        dash.cell(row=i, column=1, value=k)
        dash.cell(row=i, column=2, value=v)

    # ---- Bank_Reconciliation ----
    br = wb.create_sheet("Bank_Reconciliation")
    rec_view = recon.rename(
        columns={"amount_diff": "Difference", "status": "Match Status", "confidence": "Confidence"}
    )
    rec_view = rec_view[
        [
            "invoice_id",
            "payment_id",
            "bank_reference",
            "Match Status",
            "Difference",
            "Confidence",
            "notes",
        ]
    ]
    rec_view.columns = [
        "Invoice ID",
        "Payment ID",
        "Bank Reference",
        "Match Status",
        "Difference",
        "Confidence",
        "Notes",
    ]
    _write_df(br, rec_view)
    br.conditional_formatting.add(
        f"D2:D{len(rec_view) + 1}", CellIsRule(operator="notEqual", formula=['"MATCHED"'], fill=RED)
    )

    # ---- Invoice_Register ----
    ir = wb.create_sheet("Invoice_Register")
    vi = pd.read_csv(raw / "vendor_invoices.csv")
    _write_df(ir, vi)

    # ---- Payment_Register ----
    pr = wb.create_sheet("Payment_Register")
    pay = pd.read_csv(raw / "payments.csv")
    _write_df(pr, pay)

    # ---- Vendor_Aging ----
    va = wb.create_sheet("Vendor_Aging")
    vi2 = vi.copy()
    vi2["due_date"] = pd.to_datetime(vi2["due_date"])
    asof = pd.Timestamp(C.END_DATE)
    vi2["days_overdue"] = (asof - vi2["due_date"]).dt.days

    def bucket(d):
        if d <= 0:
            return "Current"
        if d <= 30:
            return "1-30"
        if d <= 60:
            return "31-60"
        if d <= 90:
            return "61-90"
        return "90+"

    vi2["aging"] = vi2["days_overdue"].apply(bucket)
    va_df = vi2[
        [
            "invoice_id",
            "vendor_id",
            "due_date",
            "total_amount",
            "currency",
            "status",
            "days_overdue",
            "aging",
        ]
    ]
    _write_df(va, va_df)

    # ---- Inventory ----
    inv_sheet = wb.create_sheet("Inventory")
    invv = inv.copy()
    invv["inventory_value"] = invv["quantity"] * invv["unit_cost"]
    _write_df(inv_sheet, invv)

    # ---- Controls ----
    cs = wb.create_sheet("Controls")
    _write_df(cs, controls)

    # ---- Raw_Data ----
    rd = wb.create_sheet("Raw_Data")
    _write_df(rd, recon)

    for ws in wb.worksheets:
        _autosize(ws)
        ws.freeze_panes = "A2"

    out = C.BASE_DIR / "excel" / "FinanceOps_Reconciliation.xlsx"
    wb.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    build()
