"""Inventory analytics: valuation, low/over-stock, warehouse utilization."""

from __future__ import annotations

import numpy as np
import pandas as pd

SAFETY_STOCK = 50


def analyze(frames):
    inv = frames["inventory"].copy()
    wh = frames["warehouses"]
    cap = {r["warehouse_id"]: r["capacity_units"] for r in wh.to_dict("records")}

    inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"])
    # Current state = latest snapshot per (warehouse, product). The
    # inventory table stores several snapshot dates per key, so summing
    # quantity across all of them multi-counts the same stock (~4x here)
    # and inflates utilization / valuation.
    current = (
        inv.sort_values("snapshot_date")
        .groupby(["warehouse_id", "product_id"])
        .tail(1)
        .copy()
    )

    # valuation (current stock)
    current["inventory_value"] = current["quantity"] * current["unit_cost"]

    # warehouse utilization (units on hand vs capacity)
    util = (
        current.groupby("warehouse_id")["quantity"]
        .sum()
        .reset_index()
        .rename(columns={"quantity": "total_units"})
    )
    util["capacity_units"] = util["warehouse_id"].map(cap)
    util["utilization_pct"] = (
        util["total_units"] / util["capacity_units"].replace(0, np.nan) * 100
    ).round(2)

    # low / over stock per product (median-based, current stock)
    med = current.groupby("product_id")["quantity"].median()
    low = current[current["quantity"] < SAFETY_STOCK].copy()
    low["flag"] = "LOW_STOCK"
    over = current[current["quantity"] > current["product_id"].map(med) * 2].copy()
    over["flag"] = "OVERSTOCK"

    summary = {
        "total_inventory_value": float(current["inventory_value"].sum()),
        "total_units": int(current["quantity"].sum()),
        "low_stock_skus": int(low["product_id"].nunique()),
        "overstock_skus": int(over["product_id"].nunique()),
        "warehouses": int(current["warehouse_id"].nunique()),
    }
    return current, util, low, over, summary


def main():
    from validation import load_frames

    frames = load_frames()
    _inv, util, _low, _over, summary = analyze(frames)
    print("Inventory summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("\nWarehouse utilization:")
    print(util.to_string(index=False))


if __name__ == "__main__":
    main()
