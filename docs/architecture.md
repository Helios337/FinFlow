# Architecture — FinanceOps360

```
Synthetic Data Generator (Python/Faker)
        │  CSV  (data/raw/)
        ▼
PostgreSQL (docker postgres:16, port 5433)
        │
        ├── SQL analytics  (sql/*.sql, views.sql)  ──► Power BI (Service)
        │
        ├── Python pipeline
        │     reconciliation.py  → reconciliation_results
        │     validation.py      → controls_violations
        │     anomaly_detection.py → anomalies
        │     inventory_analysis.py / finance_metrics.py
        │     report_exporter.py → data/processed/*.csv
        │           │
        │           ▼
        │     Excel workbook (openpyxl)  → FinanceOps_Reconciliation.xlsx
        │
        └── FastAPI (backend/main.py)
              GET /vendors /invoices /payments /transactions
              GET /inventory /reconciliation /anomalies /metrics /controls
              POST /ai/ask  → AI Copilot

AI Copilot pipeline:
  question → LLM → SQL → validate (allowlist + SELECT-only) → Postgres
  → verified rows → LLM explanation
```

## Build order
1. `python data_generator.py`  (seeded, deterministic)
2. `docker compose up -d` then `python db_loader.py`  (schema + raw load)
3. `python persist.py`  (views + reconciliation/controls/anomalies → DB)
4. `python report_exporter.py`  (processed CSVs)
5. `python excel/build_workbook.py`  (Excel)
6. `uvicorn backend.main:app`  (API + AI)
7. Power BI: connect to Postgres, build 4 dashboards, publish to Service.

## Conventions
- Reporting currency INR; convert via `fx_rates`.
- Bank amounts signed (debit negative).
- Reconciliation status is a strict priority: DUPLICATE > CURRENCY_MISMATCH >
  AMOUNT_MISMATCH > MISSING_BANK_TRANSACTION > PARTIAL_PAYMENT > MATCHED
  (MISSING_PAYMENT when no payment exists).
