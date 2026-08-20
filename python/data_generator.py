"""FinanceOps360 synthetic data generator.

Generates realistic medical-device company data with intentionally injected
errors, then writes CSVs to data/raw/. Deterministic via config.SEED.

Run:
    python python/data_generator.py
"""
from __future__ import annotations
import csv
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

import config as C

fake = Faker()
Faker.seed(C.SEED)
random.seed(C.SEED)
np.random.seed(C.SEED)

START = date.fromisoformat(C.START_DATE)
END = date.fromisoformat(C.END_DATE)


def _rand_date():
    span = (END - START).days
    return START + timedelta(days=random.randint(0, span))


def _code(prefix, n, width=4):
    return f"{prefix}{n:0{width}d}"


# ---------------------------------------------------------------------------
# 1. FX rates (daily, INR base)
# ---------------------------------------------------------------------------
def gen_fx_rates():
    rows = []
    # starting rates: 1 unit foreign = X INR
    base = {"USD": 83.0, "EUR": 90.0, "AED": 22.6, "SGD": 62.0}
    cur = dict(base)
    d = START
    while d <= END:
        for fc, rate in cur.items():
            rows.append({
                "rate_date": d.isoformat(),
                "from_currency": fc,
                "to_currency": "INR",
                "rate": round(rate, 4),
            })
            rows.append({
                "rate_date": d.isoformat(),
                "from_currency": "INR",
                "to_currency": fc,
                "rate": round(1.0 / rate, 6),
            })
        # random walk
        for k in cur:
            cur[k] = max(1.0, cur[k] * np.random.normal(1.0, 0.01))
        d += timedelta(days=1)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. Masters
# ---------------------------------------------------------------------------
VENDOR_CATS = ["Electronics", "Mechanical Components", "Laboratory Supplies",
               "Packaging", "Logistics", "Software", "Maintenance"]
CUSTOMER_TYPES = ["Hospital", "Diagnostic Laboratory", "Research Institute", "Distributor"]
WH_NAMES = {
    "WH1": ("Bangalore DC", "India", "Bangalore", "Distribution"),
    "WH2": ("Mumbai DC", "India", "Mumbai", "Distribution"),
    "WH3": ("Delhi DC", "India", "Delhi", "Distribution"),
    "WH4": ("Hyderabad DC", "India", "Hyderabad", "Distribution"),
    "WH5": ("Singapore Hub", "Singapore", "Singapore", "Transit"),
    "WH6": ("Dubai Hub", "UAE", "Dubai", "Transit"),
    "WH7": ("Frankfurt Hub", "Germany", "Frankfurt", "Transit"),
    "WH8": ("New Jersey Hub", "USA", "Newark", "Transit"),
}
PRODUCTS = ["Slide Scanner", "Robotic Microtome", "Imaging Module",
            "Sample Processor", "Optical Components", "Replacement Parts",
            "Calibration Kit", "Reagent Pack", "Control Software License",
            "Cooling Unit"]


def gen_masters():
    vendors, customers, products, warehouses, employees = [], [], [], [], []

    countries_non_inr = ["USA", "Germany", "UAE", "Singapore", "India"]
    for i in range(1, C.VOLUMES["vendors"] + 1):
        ctry = random.choice(countries_non_inr)
        cur = "INR" if ctry == "India" else random.choice(["USD", "EUR", "AED", "SGD"])
        vendors.append({
            "vendor_id": _code("V", i),
            "vendor_name": fake.company(),
            "country": ctry,
            "region": "Domestic" if ctry == "India" else "International",
            "vendor_category": random.choice(VENDOR_CATS),
            "payment_terms_days": random.choice([15, 30, 45, 60]),
            "currency": cur,
            "status": "active",
        })

    for i in range(1, C.VOLUMES["customers"] + 1):
        ctry = random.choice(["India", "USA", "Germany", "UAE", "Singapore"])
        cur = "INR" if ctry == "India" else random.choice(["USD", "EUR", "AED", "SGD"])
        customers.append({
            "customer_id": _code("C", i),
            "customer_name": fake.company(),
            "country": ctry,
            "region": "Domestic" if ctry == "India" else "International",
            "customer_type": random.choice(CUSTOMER_TYPES),
            "currency": cur,
            "status": "active",
        })

    for i in range(1, C.VOLUMES["products"] + 1):
        name = f"{random.choice(PRODUCTS)} {fake.color_name().title()}"
        cost = round(np.random.lognormal(9, 1), 2)
        products.append({
            "product_id": _code("P", i),
            "product_name": name,
            "category": random.choice(VENDOR_CATS),
            "unit_cost": cost,
            "selling_price": round(cost * random.uniform(1.3, 2.2), 2),
            "currency": "INR",
        })

    for wid, (nm, ctry, city, wtype) in WH_NAMES.items():
        warehouses.append({
            "warehouse_id": wid,
            "warehouse_name": nm,
            "country": ctry,
            "city": city,
            "warehouse_type": wtype,
            "capacity_units": random.randint(20000, 80000),
        })

    depts = ["Finance", "Operations", "Procurement", "Logistics", "Quality", "IT"]
    for i in range(1, C.VOLUMES["employees"] + 1):
        employees.append({
            "employee_id": _code("E", i),
            "employee_name": fake.name(),
            "department": random.choice(depts),
            "location": random.choice([w[2] for w in WH_NAMES.values()]),
            "manager_id": None,
        })
    # assign managers
    for e in employees:
        if random.random() < 0.7:
            mgr = random.choice(employees)
            if mgr["employee_id"] != e["employee_id"]:
                e["manager_id"] = mgr["employee_id"]

    return (pd.DataFrame(vendors), pd.DataFrame(customers), pd.DataFrame(products),
            pd.DataFrame(warehouses), pd.DataFrame(employees))


# ---------------------------------------------------------------------------
# 3. Purchasing
# ---------------------------------------------------------------------------
def gen_purchasing(vendors, products, warehouses):
    pos, items = [], []
    vrows = vendors.to_dict("records")
    prows = products.to_dict("records")
    wrows = warehouses["warehouse_id"].tolist()
    for i in range(1, C.VOLUMES["purchase_orders"] + 1):
        v = random.choice(vrows)
        n_lines = random.randint(2, 8)
        chosen = random.sample(prows, n_lines)
        po_id = _code("PO", i)
        total = 0.0
        po_date = _rand_date()
        for p in chosen:
            qty = random.randint(5, 200)
            price = round(p["unit_cost"] * random.uniform(0.8, 1.1), 2)
            total += qty * price
            items.append({
                "po_item_id": len(items) + 1,
                "po_id": po_id,
                "product_id": p["product_id"],
                "quantity": qty,
                "unit_price": price,
            })
        pos.append({
            "po_id": po_id,
            "vendor_id": v["vendor_id"],
            "po_date": po_date.isoformat(),
            "warehouse_id": random.choice(wrows),
            "currency": v["currency"],
            "total_amount": round(total, 2),
            "status": "approved",
        })
    return pd.DataFrame(pos), pd.DataFrame(items)


# ---------------------------------------------------------------------------
# 4. Vendor invoices (clean)
# ---------------------------------------------------------------------------
def gen_vendor_invoices(pos, vendors):
    invs = []
    vmap = {r["vendor_id"]: r for r in vendors.to_dict("records")}
    pmap = {r["po_id"]: r for r in pos.to_dict("records")}
    n = C.VOLUMES["vendor_invoices"]
    po_ids = pos["po_id"].tolist()
    for i in range(1, n + 1):
        po_id = random.choice(po_ids) if random.random() < 0.7 else None
        if po_id:
            v = vmap[pmap[po_id]["vendor_id"]]
        else:
            v = random.choice(list(vmap.values()))
        inv_date = _rand_date()
        terms = v["payment_terms_days"]
        due = inv_date + timedelta(days=terms)
        subtotal = round(np.random.lognormal(10, 1), 2)
        tax = round(subtotal * random.uniform(0.05, 0.18), 2)
        invs.append({
            "invoice_id": _code("INV", i),
            "vendor_id": v["vendor_id"],
            "po_id": po_id,
            "invoice_date": inv_date.isoformat(),
            "due_date": due.isoformat(),
            "currency": v["currency"],
            "subtotal": subtotal,
            "tax": tax,
            "total_amount": round(subtotal + tax, 2),
            "status": "Paid" if random.random() < 0.75 else "Pending",
            "injected_error": None,
        })
    return pd.DataFrame(invs)


# ---------------------------------------------------------------------------
# 5. Payments + Bank transactions (clean)
# ---------------------------------------------------------------------------
def gen_payments_and_bank(invs, vendors):
    payments = []
    bank = []
    vmap = {r["vendor_id"]: r for r in vendors.to_dict("records")}
    invs = invs.sample(frac=1, random_state=C.SEED).reset_index(drop=True)
    n_pay = C.VOLUMES["payments"]
    pay_seq = 1
    bank_seq = 1
    for _, inv in invs.iterrows():
        if len(payments) >= n_pay:
            break
        v = vmap[inv["vendor_id"]]
        pay_date = date.fromisoformat(inv["invoice_date"]) + timedelta(days=random.randint(1, 40))
        if pay_date > END:
            pay_date = END
        full = inv["total_amount"]
        if random.random() < 0.05:
            amount = round(full * random.uniform(0.6, 0.9), 2)  # partial
        else:
            amount = full
        ref = f"BNK{_code('', pay_seq, 6)}"
        payments.append({
            "payment_id": _code("PAY", pay_seq),
            "invoice_id": inv["invoice_id"],
            "payment_date": pay_date.isoformat(),
            "amount": round(amount, 2),
            "currency": inv["currency"],
            "bank_reference": ref,
            "payment_method": random.choice(["NEFT", "RTGS", "Wire", "Check"]),
            "status": "completed",
            "approval_status": "Approved" if amount < 5_000_000 else random.choice(["Approved", "Pending"]),
            "approved_by": fake.name() if amount < 5_000_000 else None,
            "injected_error": None,
        })
        bank.append(_bank_row(bank_seq, ref, -amount, inv["currency"], v["vendor_name"], pay_date, "Debit"))
        bank_seq += 1
        pay_seq += 1

    # Extra bank transactions: AR receipts, fees, transfers, refunds, noise
    cust_total = C.VOLUMES["bank_transactions"] - len(bank)
    for _ in range(cust_total):
        ttype = random.choice(["Credit", "Credit", "Fee", "Transfer", "Refund", "Credit"])
        amt = round(np.random.lognormal(10, 1), 2)
        if ttype == "Debit":
            amt = -amt
        elif ttype == "Fee":
            amt = -round(random.uniform(10, 500), 2)
        bank.append(_bank_row(bank_seq, f"BNK{_code('X', bank_seq, 6)}", amt, "INR",
                               fake.company(), _rand_date(), ttype))
        bank_seq += 1
    return pd.DataFrame(payments), pd.DataFrame(bank)


def _bank_row(seq, ref, amount, cur, cp, dt, ttype):
    return {
        "transaction_id": f"TX{seq:06d}",
        "transaction_date": dt.isoformat() if isinstance(dt, date) else dt,
        "transaction_type": ttype,
        "description": f"{ttype} {cp}",
        "reference": ref,
        "amount": round(amount, 2),
        "currency": cur,
        "bank_account": random.choice(["ACC-IND", "ACC-SG", "ACC-US"]),
        "counterparty": cp,
        "injected_error": None,
    }


# ---------------------------------------------------------------------------
# 6. Customer invoices (receivables)
# ---------------------------------------------------------------------------
def gen_customer_invoices(customers):
    rows = []
    cmap = {r["customer_id"]: r for r in customers.to_dict("records")}
    for i in range(1, C.VOLUMES["customer_invoices"] + 1):
        c = random.choice(list(cmap.values()))
        inv_date = _rand_date()
        due = inv_date + timedelta(days=random.choice([15, 30, 45]))
        subtotal = round(np.random.lognormal(10.2, 1), 2)
        tax = round(subtotal * random.uniform(0.05, 0.18), 2)
        rows.append({
            "customer_invoice_id": _code("CINV", i),
            "customer_id": c["customer_id"],
            "invoice_date": inv_date.isoformat(),
            "due_date": due.isoformat(),
            "currency": c["currency"],
            "subtotal": subtotal,
            "tax": tax,
            "total_amount": round(subtotal + tax, 2),
            "status": "Paid" if random.random() < 0.7 else "Pending",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 7. Inventory (movements + snapshots derived from movements)
# ---------------------------------------------------------------------------
def gen_inventory(products, warehouses):
    movements = []
    prows = products.to_dict("records")
    whs = warehouses["warehouse_id"].tolist()
    stock = {}  # (wh, prod) -> qty
    mseq = 1

    def add_movement(prod, src, dst, qty, mtype, dt, cost):
        nonlocal mseq
        movements.append({
            "movement_id": mseq,
            "product_id": prod,
            "source_warehouse": src,
            "destination_warehouse": dst,
            "quantity": qty,
            "unit_cost": round(cost, 2),
            "movement_date": dt.isoformat(),
            "movement_type": mtype,
            "reference": f"MOV{mseq:06d}",
        })
        mseq += 1

    # seed initial stock
    for p in random.sample(prows, min(60, len(prows))):
        wh = random.choice(whs)
        stock[(wh, p["product_id"])] = random.randint(50, 500)

    mtypes = ["Purchase", "Sale", "Transfer", "Return", "Adjustment"]
    for _ in range(C.VOLUMES["inventory_movements"]):
        p = random.choice(prows)
        mtype = random.choice(mtypes)
        dt = _rand_date()
        if mtype == "Purchase":
            wh = random.choice(whs)
            q = random.randint(10, 300)
            stock[(wh, p["product_id"])] = stock.get((wh, p["product_id"]), 0) + q
            add_movement(p["product_id"], None, wh, q, mtype, dt, p["unit_cost"])
        elif mtype == "Sale":
            wh = random.choice(whs)
            cur = stock.get((wh, p["product_id"]), 0)
            q = min(random.randint(1, 100), max(0, cur))
            stock[(wh, p["product_id"])] = cur - q
            add_movement(p["product_id"], wh, None, q, mtype, dt, p["unit_cost"])
        elif mtype == "Transfer":
            a, b = random.sample(whs, 2)
            cur = stock.get((a, p["product_id"]), 0)
            q = min(random.randint(1, 80), max(0, cur))
            stock[(a, p["product_id"])] = cur - q
            stock[(b, p["product_id"])] = stock.get((b, p["product_id"]), 0) + q
            add_movement(p["product_id"], a, b, q, mtype, dt, p["unit_cost"])
        elif mtype == "Return":
            wh = random.choice(whs)
            q = random.randint(1, 50)
            stock[(wh, p["product_id"])] = stock.get((wh, p["product_id"]), 0) + q
            add_movement(p["product_id"], None, wh, q, mtype, dt, p["unit_cost"])
        else:  # Adjustment
            wh = random.choice(whs)
            q = random.randint(-30, 30)
            stock[(wh, p["product_id"])] = stock.get((wh, p["product_id"]), 0) + q
            add_movement(p["product_id"], wh, wh, q, mtype, dt, p["unit_cost"])

    # Snapshots at month ends
    snapshots = []
    pmap = {p["product_id"]: p for p in prows}
    sseq = 1
    for mdate in C.INVENTORY_MONTHS:
        md = date.fromisoformat(mdate)
        # recompute stock at md by replaying movements
        snap_stock = {}
        for m in movements:
            if date.fromisoformat(m["movement_date"]) <= md:
                mtype = m["movement_type"]
                q = m["quantity"]
                prod = m["product_id"]
                if mtype in ("Purchase", "Return"):
                    k = (m["destination_warehouse"], prod)
                    snap_stock[k] = snap_stock.get(k, 0) + q
                elif mtype == "Sale":
                    k = (m["source_warehouse"], prod)
                    snap_stock[k] = snap_stock.get(k, 0) - q
                elif mtype == "Transfer":
                    a = (m["source_warehouse"], prod)
                    b = (m["destination_warehouse"], prod)
                    snap_stock[a] = snap_stock.get(a, 0) - q
                    snap_stock[b] = snap_stock.get(b, 0) + q
                elif mtype == "Adjustment":
                    k = (m["source_warehouse"], prod)
                    snap_stock[k] = snap_stock.get(k, 0) + q
        for (wh, prod), qty in snap_stock.items():
            if qty <= 0:
                continue
            cost = pmap[prod]["unit_cost"]
            snapshots.append({
                "inventory_id": sseq,
                "warehouse_id": wh,
                "product_id": prod,
                "quantity": qty,
                "unit_cost": round(cost, 2),
                "inventory_value": round(qty * cost, 2),
                "snapshot_date": mdate,
                "injected_error": None,
            })
            sseq += 1
            if len(snapshots) >= C.VOLUMES["inventory_snapshots"]:
                break
        if len(snapshots) >= C.VOLUMES["inventory_snapshots"]:
            break
    return pd.DataFrame(movements), pd.DataFrame(snapshots)


# ---------------------------------------------------------------------------
# 8. Expenses
# ---------------------------------------------------------------------------
def gen_expenses(employees):
    rows = []
    for i in range(1, C.VOLUMES["expenses"] + 1):
        e = random.choice(employees["employee_id"].tolist())
        rows.append({
            "expense_id": _code("EXP", i),
            "employee_id": e,
            "expense_date": _rand_date().isoformat(),
            "category": random.choice(["Travel", "Software", "Logistics", "Office", "Training"]),
            "amount": round(np.random.lognormal(8, 1), 2),
            "currency": "INR",
            "approval_status": "Approved" if random.random() < 0.85 else "Pending",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 9. Error injection (coordinate with reconciliation contract)
# ---------------------------------------------------------------------------
def inject_errors(invs, payments, bank, snapshots, vendors):
    rng = random.Random(C.SEED + 1)
    vmap = vendors.set_index("vendor_id").to_dict("index")

    def pick(df, col, rate, used=None):
        n = max(1, int(len(df) * rate))
        pool = [i for i in range(len(df)) if (used is None or i not in used)]
        idx = rng.sample(pool, min(n, len(pool)))
        if used is not None:
            used.update(idx)
        return idx

    # Duplicate invoices (clone, new id, same vendor/date/amount)
    idx = pick(invs, "invoice_id", C.ERROR_RATES["duplicate_invoice"])
    dups = []
    for i in idx:
        r = invs.iloc[i].to_dict()
        r["invoice_id"] = r["invoice_id"] + "-D"
        r["injected_error"] = "duplicate_invoice"
        dups.append(r)
    invs = pd.concat([invs, pd.DataFrame(dups)], ignore_index=True)

    # Missing payment FIRST so later payment injections are never dropped.
    idx = pick(payments, "payment_id", C.ERROR_RATES["missing_payment"])
    payments = payments.drop(payments.index[idx]).reset_index(drop=True)
    # (reconciliation detects MISSING_PAYMENT for the orphaned invoices)

    # Natural duplicate (vendor+amount) keys — avoid injecting payment errors
    # on these so DUPLICATE priority doesn't mask the intended status.
    _d = invs.copy()
    _d["key"] = _d["vendor_id"].astype(str) + "|" + _d["total_amount"].astype(str)
    dup_keys = set(_d["key"][_d.duplicated(subset=["key"], keep=False)])

    used_pay = set()
    # Amount mismatch: payment amount > invoice total (overpayment)
    idx = pick(payments, "payment_id", C.ERROR_RATES["amount_mismatch"], used_pay)
    for i in idx:
        inv_id = payments.iloc[i]["invoice_id"]
        inv = invs[invs["invoice_id"] == inv_id]
        if len(inv):
            tot = inv.iloc[0]["total_amount"]
            if f"{inv.iloc[0]['vendor_id']}|{tot}" in dup_keys:
                continue
            payments.iat[i, payments.columns.get_loc("amount")] = round(tot * rng.uniform(1.05, 1.15), 2)
            payments.iat[i, payments.columns.get_loc("injected_error")] = "amount_mismatch"

    # Currency mismatch: payment currency != invoice currency (disjoint)
    idx = pick(payments, "payment_id", C.ERROR_RATES["currency_mismatch"], used_pay)
    for i in idx:
        cur = payments.iloc[i]["currency"]
        alt = rng.choice([c for c in C.CURRENCIES if c != cur])
        inv_id = payments.iloc[i]["invoice_id"]
        inv = invs[invs["invoice_id"] == inv_id]
        if len(inv) and f"{inv.iloc[0]['vendor_id']}|{inv.iloc[0]['total_amount']}" in dup_keys:
            continue
        payments.iat[i, payments.columns.get_loc("currency")] = alt
        payments.iat[i, payments.columns.get_loc("injected_error")] = "currency_mismatch"

    # Timing difference: payment far past terms (disjoint)
    idx = pick(payments, "payment_id", C.ERROR_RATES["timing_diff"], used_pay)
    for i in idx:
        inv_id = payments.iloc[i]["invoice_id"]
        inv = invs[invs["invoice_id"] == inv_id]
        if len(inv):
            base = date.fromisoformat(inv.iloc[0]["invoice_date"])
            pd_ = base + timedelta(days=rng.choice([120, 150, 180]))
            payments.iat[i, payments.columns.get_loc("payment_date")] = pd_.isoformat()
            payments.iat[i, payments.columns.get_loc("injected_error")] = "timing_diff"

    used_bank = set()
    # Wrong vendor mapping: bank counterparty != vendor name (disjoint)
    idx = pick(bank, "transaction_id", C.ERROR_RATES["wrong_vendor_mapping"], used_bank)
    for i in idx:
        if bank.iloc[i]["transaction_type"] == "Debit":
            bank.iat[i, bank.columns.get_loc("counterparty")] = f"UNKNOWN-COUNTERPARTY-{rng.randint(1000, 9999)}"
            bank.iat[i, bank.columns.get_loc("injected_error")] = "wrong_vendor_mapping"

    # Duplicate bank transaction (disjoint)
    idx = pick(bank, "transaction_id", C.ERROR_RATES["duplicate_bank"], used_bank)
    dups = []
    for i in idx:
        r = bank.iloc[i].to_dict()
        r["transaction_id"] = r["transaction_id"] + "-D"
        r["injected_error"] = "duplicate_bank"
        dups.append(r)
    bank = pd.concat([bank, pd.DataFrame(dups)], ignore_index=True)

    # Unusual transaction: very large bank debit (disjoint)
    idx = pick(bank, "transaction_id", C.ERROR_RATES["unusual_txn"], used_bank)
    for i in idx:
        if bank.iloc[i]["amount"] > 0:
            bank.iat[i, bank.columns.get_loc("amount")] = -abs(bank.iloc[i]["amount"]) * rng.uniform(5, 12)
        else:
            bank.iat[i, bank.columns.get_loc("amount")] = bank.iloc[i]["amount"] * rng.uniform(5, 12)
        bank.iat[i, bank.columns.get_loc("injected_error")] = "unusual_txn"

    # Inventory mismatch: alter snapshot value / quantity
    idx = pick(snapshots, "inventory_id", C.ERROR_RATES["inventory_mismatch"])
    for i in idx:
        q = snapshots.iloc[i]["quantity"]
        snapshots.iat[i, snapshots.columns.get_loc("quantity")] = int(q * rng.uniform(0.3, 1.8))
        snapshots.iat[i, snapshots.columns.get_loc("inventory_value")] = round(
            snapshots.iloc[i]["quantity"] * snapshots.iloc[i]["unit_cost"], 2)
        snapshots.iat[i, snapshots.columns.get_loc("injected_error")] = "inventory_mismatch"

    return invs, payments, bank, snapshots


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Generating FX rates ...")
    fx = gen_fx_rates()
    print("Generating masters ...")
    vendors, customers, products, warehouses, employees = gen_masters()
    print("Generating purchasing ...")
    pos, items = gen_purchasing(vendors, products, warehouses)
    print("Generating vendor invoices ...")
    invs = gen_vendor_invoices(pos, vendors)
    print("Generating payments + bank ...")
    payments, bank = gen_payments_and_bank(invs, vendors)
    print("Generating customer invoices ...")
    cinvs = gen_customer_invoices(customers)
    print("Generating inventory ...")
    movements, snapshots = gen_inventory(products, warehouses)
    print("Generating expenses ...")
    expenses = gen_expenses(employees)
    print("Injecting errors ...")
    invs, payments, bank, snapshots = inject_errors(invs, payments, bank, snapshots, vendors)

    out = {
        "fx_rates.csv": fx,
        "vendors.csv": vendors,
        "customers.csv": customers,
        "products.csv": products,
        "warehouses.csv": warehouses,
        "employees.csv": employees,
        "purchase_orders.csv": pos,
        "purchase_order_items.csv": items,
        "vendor_invoices.csv": invs,
        "payments.csv": payments,
        "bank_transactions.csv": bank,
        "customer_invoices.csv": cinvs,
        "inventory_movements.csv": movements,
        "inventory.csv": snapshots,
        "expenses.csv": expenses,
    }
    for name, df in out.items():
        df.to_csv(C.RAW_DIR / name, index=False)
        print(f"  wrote {name}: {len(df)} rows")
    print("Done.")


if __name__ == "__main__":
    main()
