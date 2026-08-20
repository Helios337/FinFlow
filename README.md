# FinFlow — Financial Operations Analytics & Automation Platform

End-to-end finance & supply-chain analytics platform that reconciles
transactions, detects discrepancies/anomalies, tracks inventory, and exposes
executive reporting via SQL, Excel, Power BI, FastAPI and an AI copilot.


## Stack
PostgreSQL · SQL · Python (pandas/numpy/Faker) · Excel (openpyxl) · Power BI
(Service) · FastAPI · Pydantic · AI (OpenAI-compatible, read-only).

## Repository layout
```
sql/        schema.sql, views.sql, finance_metrics.sql,
            reconciliation_queries.sql, inventory_metrics.sql
python/     data_generator, db_loader, persist, reconciliation, validation,
            anomaly_detection, inventory_analysis, finance_metrics, report_exporter
backend/    main.py, db.py, schemas.py, services.py, ai/copilot.py
excel/      build_workbook.py  → FinanceOps_Reconciliation.xlsx
powerbi/    dashboard documentation + screenshots (build .pbix in VM, publish Service)
tests/      test_reconciliation, test_validation, test_metrics
docs/       business_requirements, data_dictionary, architecture,
            business_rules, ai_guardrails
data/       raw/ (generated), processed/ (reports)
```

## Quick start
```bash
cp .env.example .env            # set OPENAI_API_KEY if you want real LLM
docker compose up -d            # postgres on :5433
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python python/data_generator.py  # generate + inject errors -> data/raw
python python/db_loader.py      # schema + load -> postgres
python python/persist.py        # views + reconciliation/controls/anomalies -> DB
python python/report_exporter.py# processed CSV reports
python excel/build_workbook.py  # Excel workbook
uvicorn backend.main:app --reload   # API at http://localhost:8000/docs
```

## Modules
- **Data generation** — ~80K deterministic, seeded synthetic records with a
  documented error-injection catalogue.
- **Reconciliation engine** — strict status priority (DUPLICATE > CURRENCY_MISMATCH
  > AMOUNT_MISMATCH > MISSING_BANK > PARTIAL > MATCHED / MISSING_PAYMENT).
- **Controls** — 8 rules (C1–C8): duplicates, authorization, PO/invoice match,
  inventory identity, late payment, wrong counterparty, duplicate bank.
- **Anomaly detection** — z-score, IQR, vendor-baseline (explainable).
- **Excel** — 8-sheet reconciliation workbook with conditional formatting.
- **Power BI** — star schema + 4 dashboards (Executive, Reconciliation,
  Supply Chain, AP); author in Windows VM Desktop, publish to Service.
- **FastAPI + AI** — REST endpoints + read-only, guardrailed NL→SQL copilot.

## API
`GET /metrics /reconciliation /anomalies /inventory /vendors /invoices
/payments /transactions /controls` and `POST /ai/ask`.

## Tests
`pytest tests/` — reconciliation & control recall on injected errors, metric
sanity, and AI SQL guardrails. All green.

## Results (sample run)
- ~80K records; reconciliation match rate ~77%.
- Controls found: C1 duplicates, C4 payment>invoice, C5 inventory, C6 late,
  C7 wrong counterparty, C8 duplicate bank.
- ~800 anomalies (unusual amounts, IQR, vendor-baseline).

## Limitations / future
- Inventory turnover approximated (no COGS in model).
- Single invoice↔single payment (no split payments bridge).
- Power BI authored in Desktop (Windows VM) and published to Service.
- Isolation Forest included as optional multivariate layer.
