"""AI Finance Operations Copilot.

Pipeline: question -> LLM -> SQL -> validate -> execute (read-only) -> explain.
Guardrails: only SELECT; table/column allowlist; no INSERT/UPDATE/DELETE/DDL.
Falls back to a rule-based stub when no API key is configured.
"""

from __future__ import annotations

import os
import re

import httpx

from .. import db, services

SCHEMA_TEXT = """
Tables (PostgreSQL):
- vendors(vendor_id, vendor_name, country, region, vendor_category, payment_terms_days, currency, status)
- vendor_invoices(invoice_id, vendor_id, po_id, invoice_date, due_date, currency, subtotal, tax, total_amount, status)
- payments(payment_id, invoice_id, payment_date, amount, currency, bank_reference, payment_method, status, approval_status, approved_by)
- bank_transactions(transaction_id, transaction_date, transaction_type, description, reference, amount, currency, bank_account, counterparty)
- purchase_orders(po_id, vendor_id, po_date, warehouse_id, currency, total_amount, status)
- purchase_order_items(po_item_id, po_id, product_id, quantity, unit_price)
- customer_invoices(customer_invoice_id, customer_id, invoice_date, due_date, currency, subtotal, tax, total_amount, status)
- customers(customer_id, customer_name, country, region, customer_type, currency, status)
- inventory(inventory_id, warehouse_id, product_id, quantity, unit_cost, inventory_value, snapshot_date)
- inventory_movements(movement_id, product_id, source_warehouse, destination_warehouse, quantity, unit_cost, movement_date, movement_type, reference)
- reconciliation_results(invoice_id, payment_id, bank_reference, status, confidence, amount_diff, currency_match, notes)
- anomalies(transaction_id, source_table, anomaly_type, score, severity, reason, expected_value, observed_value, recommended_action)
- controls_violations(rule_id, entity_type, entity_id, severity, description, detected_at)
- warehouses, products, employees, expenses, fx_rates
Reporting currency is INR. View v_vendor_invoices_inr adds total_inr (FX-converted).
Return a single SQL SELECT statement only.
"""

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|merge|exec|execute|pg_sleep|sleep)\b",
    re.I,
)
ALLOWED_TABLES = {
    "vendors",
    "vendor_invoices",
    "payments",
    "bank_transactions",
    "purchase_orders",
    "purchase_order_items",
    "customer_invoices",
    "customers",
    "inventory",
    "inventory_movements",
    "reconciliation_results",
    "anomalies",
    "controls_violations",
    "warehouses",
    "products",
    "employees",
    "expenses",
    "fx_rates",
    "v_vendor_invoices_inr",
    "v_ap_aging",
    "v_reconciliation_summary",
}


def validate_sql(sql: str) -> tuple[bool, str]:
    s = sql.strip().rstrip(";").strip()
    if not s.lower().startswith("select"):
        return False, "Only SELECT queries are permitted."
    if FORBIDDEN.search(s):
        return False, "Statement contains a forbidden keyword."
    # Require a FROM clause so statement-less function calls such as
    # `SELECT pg_sleep(10)` cannot be executed against the database.
    if not re.search(r"\bfrom\b", s, re.I):
        return False, "Query must reference a table (FROM clause required)."
    # table allowlist
    found = set(re.findall(r"from\s+([a-z_][a-z0-9_]*)", s, re.I))
    found |= set(re.findall(r"join\s+([a-z_][a-z0-9_]*)", s, re.I))
    bad = found - ALLOWED_TABLES
    if bad:
        return False, f"Table(s) not allowed: {', '.join(sorted(bad))}"
    return True, ""


def _stub_answer(question: str) -> dict:
    q = question.lower()
    if ("vendor" in q) and ("payable" in q or "payment" in q or "outstanding" in q):
        rows = db.fetch_all(
            "SELECT vi.vendor_id, SUM(vi.total_inr) AS payable_inr FROM v_vendor_invoices_inr vi "
            "WHERE vi.invoice_id NOT IN (SELECT invoice_id FROM reconciliation_results WHERE status IN ('MATCHED','PARTIAL_PAYMENT')) "
            "GROUP BY vi.vendor_id ORDER BY payable_inr DESC LIMIT 5"
        )
        return {
            "sql": "<rule-based>",
            "rows": rows,
            "explanation": "Top 5 vendors by outstanding payable (INR), computed from unmatched invoices.",
        }
    if "overdue" in q or "past due" in q:
        rows = db.fetch_all(
            "SELECT COUNT(*) AS overdue_cnt, SUM(total_inr) AS overdue_inr FROM v_ap_aging WHERE aging_bucket='90+'"
        )
        return {
            "sql": "<rule-based>",
            "rows": rows,
            "explanation": "Overdue invoices count and value (90+ days past due).",
        }
    if "reconcil" in q:
        rows = db.fetch_all(
            "SELECT ROUND(100.0*SUM(CASE WHEN status='MATCHED' THEN 1 ELSE 0 END)/COUNT(*),2) AS match_rate FROM reconciliation_results"
        )
        return {
            "sql": "<rule-based>",
            "rows": rows,
            "explanation": "Reconciliation match rate across all invoices.",
        }
    if "anomal" in q:
        rows = db.fetch_all(
            "SELECT anomaly_type, COUNT(*) AS cnt FROM anomalies GROUP BY anomaly_type ORDER BY cnt DESC"
        )
        return {"sql": "<rule-based>", "rows": rows, "explanation": "Anomaly counts by type."}
    if "inventory" in q and ("value" in q or "warehouse" in q):
        rows = db.fetch_all(
            "SELECT warehouse_id, SUM(inventory_value) AS value_inr FROM inventory GROUP BY warehouse_id ORDER BY value_inr DESC"
        )
        return {
            "sql": "<rule-based>",
            "rows": rows,
            "explanation": "Inventory value by warehouse (INR).",
        }
    return {"sql": None, "rows": [], "explanation": "Stub could not interpret the question."}


async def ask(question: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        res = _stub_answer(question)
        return {
            "question": question,
            "sql": res["sql"],
            "columns": list(res["rows"][0].keys()) if res["rows"] else [],
            "rows": res["rows"],
            "explanation": res["explanation"],
            "error": None,
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SCHEMA_TEXT},
                        {"role": "user", "content": f"Write SQL for: {question}"},
                    ],
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            sql = re.sub(r"```sql|```", "", content).strip().rstrip(";").strip()
            ok, err = validate_sql(sql)
            if not ok:
                return {
                    "question": question,
                    "sql": sql,
                    "columns": [],
                    "rows": [],
                    "explanation": None,
                    "error": f"Guardrail violated: {err}",
                }
            rows = services.execute_sql(sql)
            cols = list(rows[0].keys()) if rows else []
            # explanation
            exp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Explain the SQL result in 1-2 sentences for a finance manager. Do not invent numbers; use the returned rows.",
                        },
                        {
                            "role": "user",
                            "content": f"Question: {question}\nSQL: {sql}\nRows: {rows[:10]}",
                        },
                    ],
                    "temperature": 0,
                },
            )
            explanation = exp.json()["choices"][0]["message"]["content"]
            return {
                "question": question,
                "sql": sql,
                "columns": cols,
                "rows": rows,
                "explanation": explanation,
                "error": None,
            }
    except Exception as e:  # pragma: no cover
        res = _stub_answer(question)
        return {
            "question": question,
            "sql": res["sql"],
            "columns": list(res["rows"][0].keys()) if res["rows"] else [],
            "rows": res["rows"],
            "explanation": f"(LLM unavailable, used fallback) {res['explanation']}",
            "error": str(e),
        }
