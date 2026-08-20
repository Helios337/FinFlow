"""Financial controls & validation framework.

Implements:
  C1  Duplicate invoice control
  C2  Payment authorization control
  C3  Invoice <= PO amount
  C4  Payment <= invoice outstanding
  C5  Inventory reconciliation (movements -> snapshot)
  C6  Late / timing-difference payment
  C7  Bank counterparty != vendor (wrong mapping)
  C8  Duplicate bank transaction
"""
from __future__ import annotations
from bisect import bisect_right
from datetime import date
import difflib

import pandas as pd
import numpy as np

import config as C

AUTH_THRESHOLD = 5_000_000  # INR


def load_frames():
    raw = C.RAW_DIR
    return {k: pd.read_csv(raw / f"{k}.csv") for k in [
        "vendor_invoices", "payments", "bank_transactions", "purchase_orders",
        "inventory", "inventory_movements", "vendors", "warehouses",
        "customer_invoices",
    ]}


def _violation(rule_id, entity_type, entity_id, severity, description):
    return {
        "rule_id": rule_id, "entity_type": entity_type, "entity_id": str(entity_id),
        "severity": severity, "description": description,
    }


def run_controls(frames):
    vi = frames["vendor_invoices"]
    pay = frames["payments"]
    bank = frames["bank_transactions"]
    po = frames["purchase_orders"]
    inv = frames["inventory"]
    mov = frames["inventory_movements"]
    vmap = {r["vendor_id"]: r for r in frames["vendors"].to_dict("records")}
    vio = []

    # C1 duplicate invoice (vendor + amount + near date)
    vi2 = vi.copy()
    vi2["d"] = pd.to_datetime(vi2["invoice_date"]).dt.date.astype(str)
    dup_mask = vi2.duplicated(subset=["vendor_id", "total_amount"], keep=False)
    for _, r in vi2[dup_mask].iterrows():
        vio.append(_violation("C1", "vendor_invoice", r["invoice_id"], "HIGH",
                              "Duplicate invoice (same vendor + amount)."))

    # C2 payment authorization
    over = pay[(pay["amount"] > AUTH_THRESHOLD) & (pay["approval_status"] != "Approved")]
    for _, r in over.iterrows():
        vio.append(_violation("C2", "payment", r["payment_id"], "HIGH",
                              f"Payment {r['amount']} exceeds auth threshold without approval."))

    # C3 invoice <= PO amount
    pomap = {r["po_id"]: r for r in po.to_dict("records")}
    for _, r in vi[vi["po_id"].notna()].iterrows():
        p = pomap.get(r["po_id"])
        if p is not None and float(r["total_amount"]) > float(p["total_amount"]) * 1.001:
            vio.append(_violation("C3", "vendor_invoice", r["invoice_id"], "MEDIUM",
                                  "Invoice total exceeds linked PO amount."))

    # C4 payment <= invoice outstanding
    invmap = {r["invoice_id"]: r for r in vi.to_dict("records")}
    for _, r in pay.iterrows():
        invr = invmap.get(r["invoice_id"])
        if invr is not None and float(r["amount"]) > float(invr["total_amount"]) * 1.001:
            vio.append(_violation("C4", "payment", r["payment_id"], "MEDIUM",
                                  "Payment exceeds invoice total."))

    # C5 inventory reconciliation (net movements up to snapshot date)
    cum = _build_inventory_cumsum(mov)
    inv = inv.copy()
    inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"]).dt.date
    for _, r in inv.iterrows():
        net = _lookup(cum, r["warehouse_id"], r["product_id"], r["snapshot_date"])
        if net is not None and abs(net - int(r["quantity"])) > max(1, 0.01 * abs(net)):
            vio.append(_violation("C5", "inventory", r["inventory_id"], "HIGH",
                                  f"Snapshot qty {int(r['quantity'])} != computed {net}."))

    # C6 timing difference (payment far past terms)
    vi_date = {r["invoice_id"]: r for r in vi.to_dict("records")}
    for _, r in pay.iterrows():
        invr = vi_date.get(r["invoice_id"])
        if invr is None:
            continue
        v = vmap.get(invr["vendor_id"])
        terms = int(v["payment_terms_days"]) if v else 30
        pdate = pd.to_datetime(r["payment_date"]).date()
        idate = pd.to_datetime(invr["invoice_date"]).date()
        if (pdate - idate).days > terms + 30:
            vio.append(_violation("C6", "payment", r["payment_id"], "MEDIUM",
                                  f"Payment { (pdate-idate).days }d after invoice (terms {terms})."))

    # C7 wrong vendor mapping (bank counterparty != vendor)
    pref_map = {r["bank_reference"]: r["invoice_id"] for r in pay.to_dict("records")}
    for _, r in bank[bank["transaction_type"].isin(["Debit", "Transfer"])].iterrows():
        pref = r["reference"]
        inv_id = pref_map.get(pref)
        if inv_id is None:
            continue
        invr = vi_date.get(inv_id)
        if invr is None:
            continue
        v = vmap.get(invr["vendor_id"])
        if v:
            cp = str(r.get("counterparty", ""))
            ratio = difflib.SequenceMatcher(None, v["vendor_name"].lower(), cp.lower()).ratio()
            if ratio < 0.6:
                vio.append(_violation("C7", "bank_transaction", r["transaction_id"], "MEDIUM",
                                      f"Counterparty '{cp}' != vendor '{v['vendor_name']}'."))

    # C8 duplicate bank transaction (reference + amount + type)
    bank2 = bank.copy()
    bank2["amt"] = bank2["amount"].astype(float)
    dupb = bank2.duplicated(subset=["reference", "amt", "transaction_type"], keep=False)
    for _, r in bank2[dupb].iterrows():
        vio.append(_violation("C8", "bank_transaction", r["transaction_id"], "HIGH",
                              "Duplicate bank transaction (reference + amount + type)."))

    return pd.DataFrame(vio)


def _build_inventory_cumsum(mov):
    rows = []
    for _, m in mov.iterrows():
        q = int(m["quantity"])
        mtype = m["movement_type"]
        dt = pd.to_datetime(m["movement_date"]).date().toordinal()
        if mtype in ("Purchase", "Return"):
            rows.append((m["destination_warehouse"], m["product_id"], dt, q))
        elif mtype == "Sale":
            rows.append((m["source_warehouse"], m["product_id"], dt, -q))
        elif mtype == "Transfer":
            rows.append((m["source_warehouse"], m["product_id"], dt, -q))
            rows.append((m["destination_warehouse"], m["product_id"], dt, q))
        elif mtype == "Adjustment":
            rows.append((m["source_warehouse"], m["product_id"], dt, q))
    df = pd.DataFrame(rows, columns=["wh", "prod", "ord", "qty"])
    df = df.groupby(["wh", "prod", "ord"])["qty"].sum().reset_index()
    cum = {}
    for (wh, prod), g in df.groupby(["wh", "prod"]):
        g = g.sort_values("ord")
        running = 0
        series = []
        for _, r in g.iterrows():
            running += int(r["qty"])
            series.append((int(r["ord"]), running))
        cum[(wh, prod)] = series
    return cum


def _lookup(cum, wh, prod, d):
    series = cum.get((wh, prod))
    if not series:
        return None
    ordv = d.toordinal()
    idx = bisect_right(series, (ordv, float("inf")))
    if idx == 0:
        return 0
    return series[idx - 1][1]


def main():
    frames = load_frames()
    vio = run_controls(frames)
    out = C.PROCESSED_DIR / "controls_report.csv"
    vio.to_csv(out, index=False)
    print(f"Wrote {out}: {len(vio)} violations")
    if len(vio):
        print(vio["rule_id"].value_counts().to_string())


if __name__ == "__main__":
    main()
