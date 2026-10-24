# FinFlow - Financial Operations Analytics & Automation Platform

![CI](https://github.com/Helios337/FinFlow/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

FinFlow (service name "FinanceOps360") is an end-to-end financial operations analytics and automation platform.
It ingests a deterministic synthetic ledger for a medical-device company, reconciles invoices to payments to bank transactions, detects discrepancies and anomalies, evaluates eight financial controls, and exposes executive reporting through SQL, Excel, Power BI, a FastAPI REST API, and a guardrailed AI copilot.

The reporting currency is INR, with all non-INR amounts converted using daily FX rates before aggregation.

## Highlights

- **Deterministic synthetic ledger** - ~80K rows across 14 tables, seeded and reproducible, with a documented error-injection catalogue.
- **Three-way reconciliation engine** - invoice -> payment -> bank with a strict, mutually exclusive status priority.
- **Eight automated financial controls** (C1-C8) covering duplicates, authorization, PO/invoice matching, inventory identity, late payment, wrong counterparty, and duplicate bank entries.
- **Explainable anomaly detection** - z-score, IQR, and vendor-baseline methods, with an optional Isolation Forest layer.
- **Multi-currency reporting** - INR base currency with FX conversion applied consistently across SQL, Python, Excel, and Power BI.
- **AI copilot** - natural-language to validated, read-only SQL, with no fabricated numbers.
- **Four executive dashboards** - Executive Finance, Reconciliation, Supply Chain, and Accounts Payable.
- **Fully tested** - reconciliation and control recall on injected errors, metric sanity checks, and AI SQL guardrails, all enforced in CI.

## Architecture

```
Synthetic Data Generator (Python / Faker, seeded)
        │  CSV  (data/raw/)
        ▼
PostgreSQL (docker postgres:16, host port 5433)
        │
        ├── SQL analytics (sql/*.sql, views.sql)  ──► Power BI (Service)
        │
        ├── Python pipeline
        │     reconciliation.py     → reconciliation_results
        │     validation.py         → controls_violations
        │     anomaly_detection.py  → anomalies
        │     inventory_analysis.py / finance_metrics.py
        │     report_exporter.py    → data/processed/*.csv
        │           │
        │           ▼
        │     Excel workbook (openpyxl) → FinanceOps_Reconciliation.xlsx
        │
        └── FastAPI (backend/main.py)
              GET  /vendors /invoices /payments /transactions
              GET  /inventory /reconciliation /anomalies /metrics /controls
              POST /ai/ask  → AI Copilot

AI Copilot pipeline:
  question → LLM → SQL → validate (allowlist + SELECT-only) → Postgres (read-only role)
          → verified rows → LLM explanation
```

## Repository layout

```
FinFlow/
├── sql/              schema, views, reconciliation / finance / inventory
│                     metrics, readonly_role, seed
├── python/           data_generator, db_loader, persist, reconciliation,
│                     validation, anomaly_detection, inventory_analysis,
│                     finance_metrics, report_exporter, config, db
├── backend/          FastAPI app: main, db, schemas, services, ai/copilot
├── excel/            build_workbook.py → FinanceOps_Reconciliation.xlsx
├── powerbi/          dashboard documentation + screenshots
├── notebooks/        exploratory_analysis.ipynb
├── tests/            test_reconciliation, test_validation, test_metrics
├── docs/             business_requirements, data_dictionary, architecture,
│                     business_rules, ai_guardrails
├── data/             raw/ (generated), processed/ (reports), sample/
├── .github/workflows ci.yml
├── docker-compose.yml
├── pyproject.toml    pytest + ruff configuration
├── requirements.txt
└── .env.example
```

## Technology stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 (Docker), SQLAlchemy 2, psycopg 3 |
| Analytics | Python 3.11, pandas, NumPy, scikit-learn |
| API | FastAPI, Pydantic v2, Uvicorn, httpx |
| Reporting | openpyxl (Excel), Power BI (Service) |
| Data generation | Faker, NumPy |
| Testing / quality | pytest, ruff |

## Data model

The warehouse follows a star schema with six fact tables and seven dimensions.

**Facts:** `FactVendorInvoices` (vendor_invoices + `v_vendor_invoices_inr`), `FactPayments` (payments), `FactBankTransactions` (bank_transactions), `FactInventory` (inventory), `FactExpenses` (expenses), `FactCustomerInvoices` (customer_invoices).

**Dimensions:** `DimDate`, `DimVendor`, `DimCustomer`, `DimProduct`, `DimWarehouse`, `DimEmployee`, `DimCurrency` (fx_rates).

Conventions used throughout the platform:

- All monetary amounts are positive except `bank_transactions.amount`, which is signed (debit negative, credit positive).
- `injected_error` columns are ground-truth tags for tests only and are never used by business logic.
- Invoice totals satisfy `subtotal + tax = total`, and PO totals equal the sum of their items.

See [docs/data_dictionary.md](docs/data_dictionary.md) for the full table-by-table reference.

## Reconciliation methodology

The engine performs a three-way match: invoice -> payment (by `invoice_id`) -> bank (by `payment.bank_reference`).
Each invoice is assigned exactly one mutually exclusive status using the following strict priority:

| Priority | Status | Meaning |
|---|---|---|
| 1 | `DUPLICATE` | Cloned invoice id (`-D`) or identical vendor + amount |
| 2 | `CURRENCY_MISMATCH` | Payment currency differs from invoice currency |
| 3 | `AMOUNT_MISMATCH` | Payment exceeds invoice total + tolerance (overpayment) |
| 4 | `MISSING_BANK_TRANSACTION` | Payment has no bank debit by reference |
| 5 | `PARTIAL_PAYMENT` | Payment is short of invoice total - tolerance |
| 6 | `MATCHED` | Fully matched within tolerance |
| - | `MISSING_PAYMENT` | Invoice has no payment record |

The amount tolerance is `max(0.5% of invoice total, 0.01)`.
A soft review flag is raised when the bank counterparty does not fuzzy-match the vendor name (ratio < 0.6) without changing the status.

## Financial controls

Eight rules (C1-C8) are evaluated on every run and written to `controls_violations`.

| Rule | Control | Condition |
|---|---|---|
| C1 | Duplicate invoice | Same vendor + same amount |
| C2 | Payment authorization | Amount > 5,000,000 INR and `approval_status` is not Approved |
| C3 | Invoice vs PO | Invoice total exceeds linked PO total |
| C4 | Payment vs invoice | Payment amount exceeds invoice total |
| C5 | Inventory identity | Net movements up to snapshot date do not equal snapshot quantity |
| C6 | Late payment | Payment date is beyond terms + 30 days |
| C7 | Wrong counterparty | Bank counterparty does not match vendor name (fuzzy ratio < 0.6) |
| C8 | Duplicate bank | Same reference + amount + transaction type |

## Anomaly detection

Anomalies are explainable, each tagged with a type, score, severity, and reason:

- **Z-score** on bank debit magnitudes (flagged above 3 sigma).
- **IQR** on invoice amounts (outside 1.5x IQR).
- **Vendor baseline** (invoice above vendor mean + 3 sigma).
- **Isolation Forest** as an optional multivariate layer.

## Deliverables

### Excel workbook

`excel/build_workbook.py` produces `FinanceOps_Reconciliation.xlsx` with eight sheets: Dashboard (KPIs), Bank_Reconciliation, Invoice_Register, Payment_Register, Vendor_Aging, Inventory, Controls, and Raw_Data, with conditional formatting on the reconciliation status.

### Power BI

`powerbi/` documents a star schema and four dashboards built in Power BI Desktop (Windows VM) and published to Power BI Service:

1. **Executive Finance** - revenue, expense, payables, and receivables trends; vendor spend; payment aging; reconciliation status.
2. **Reconciliation** - matched / unmatched / mismatched / duplicate counts, mismatch value, vendor-wise discrepancies, and a top-discrepancies table.
3. **Supply Chain** - inventory by warehouse, country, and category; low-stock and overstock products; warehouse utilization; movement.
4. **Accounts Payable** - outstanding payable, vendor aging (Current / 1-30 / 31-60 / 61-90 / 90+), overdue, vendor concentration, and payment delays.

Key DAX measures include Total Payables, Total Receivables, Total Revenue, Total Expenses, Outstanding and Overdue Amount, Payment Rate, On-Time Payment %, Average Payment Delay, Inventory Value (INR), Mismatch Rate, and Inventory Turnover (proxy).

### REST API

The FastAPI service (default `http://localhost:8000`) exposes interactive docs at `/docs`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/metrics` | Payables, receivables, outstanding counts, match rate, anomalies |
| GET | `/reconciliation` | Reconciliation results (`?status=`) |
| GET | `/anomalies` | Detected anomalies (`?severity=`) |
| GET | `/controls` | Control violations |
| GET | `/inventory` | Inventory snapshots |
| GET | `/vendors` | Vendor master |
| GET | `/invoices` | Vendor invoices (`?status=`) |
| GET | `/payments` | Payments |
| GET | `/transactions` | Bank transactions |
| POST | `/ai/ask` | Natural-language question to the AI copilot |

### AI copilot

The copilot is an analysis assistant, never an autonomous agent.
It answers business questions by translating them into validated, read-only SQL and then explaining the returned rows in plain English.
The guardrails enforced in `backend/ai/copilot.py` are:

1. **Read-only** - the backend and copilot connect as the `financeops_ro` role (created by `sql/readonly_role.sql` via `python/persist.py`), so writes are impossible.
2. **SELECT-only** - generated SQL must start with `SELECT`.
3. **Forbidden keywords** - `INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/CREATE/GRANT/MERGE/EXEC/EXECUTE/PG_SLEEP/SLEEP` are blocked.
4. **FROM clause required** - statement-less calls such as `SELECT pg_sleep(10)` are rejected.
5. **Table allowlist** - only known analytics tables and views may appear in FROM/JOIN.
6. **No fabricated numbers** - every figure comes from SQL or Python aggregation; the LLM only explains returned rows.
7. **Human review for actions** - the copilot never initiates payments or changes; it only reports.
8. **Graceful fallback** - with no API key configured, a rule-based stub answers common portfolio questions without an LLM.

See [docs/ai_guardrails.md](docs/ai_guardrails.md) for the full specification.

## Quick start

### Prerequisites

- Python 3.11+ and Docker (for PostgreSQL), or a local PostgreSQL 16 instance.
- An OpenAI-compatible API key only if you want the real LLM; without one the copilot runs on a built-in rule-based stub.

### Setup

```bash
cp .env.example .env            # set OPENAI_API_KEY if you want real LLM
docker compose up -d            # PostgreSQL on host port 5433

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python python/data_generator.py  # generate + inject errors -> data/raw
python python/db_loader.py       # schema + load -> PostgreSQL
python python/persist.py         # views + reconciliation/controls/anomalies -> DB
python python/report_exporter.py # processed CSV reports -> data/processed
python excel/build_workbook.py   # Excel workbook
uvicorn backend.main:app --reload  # API at http://localhost:8000/docs
```

## Configuration

All settings live in `.env` (see `.env.example`).

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` / `PASSWORD` / `DB` | `financeops` | Owner credentials |
| `POSTGRES_HOST` / `PORT` | `localhost` / `5433` | Database host and port (container 5432 maps to host 5433) |
| `POSTGRES_RO_USER` / `PASSWORD` | `financeops_ro` | Read-only role used by the API and copilot |
| `OPENAI_API_KEY` | empty | Leave empty to use the built-in rule-based stub |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for the copilot (keep temperature at 0 for deterministic SQL) |
| `FO360_SEED` | `42` | Seed for deterministic data generation |

## Testing

```bash
python python/data_generator.py  # tests read data/raw/ (gitignored)
pytest tests/ -v
```

The suite covers reconciliation and control recall on injected errors, metric sanity, and AI SQL guardrails.
The CI workflow generates the data, lints with Ruff, and runs the tests automatically.

## Results (sample run)
| Metric | Value |
|---|---|
| Records generated | ~80K rows across 14 tables (seeded, deterministic) |
| Reconciliation match rate | ~77% |
| Controls triggered | C1 duplicates, C4 payment > invoice, C5 inventory, C6 late, C7 wrong counterparty, C8 duplicate bank |
| Anomalies detected | ~800 (unusual amounts, IQR, vendor-baseline) |

## Limitations and roadmap

- Inventory turnover is approximated because the model has no COGS.
- The data model assumes a single invoice-to-single payment mapping (no split-payments bridge).
- Power BI dashboards are authored in Desktop on a Windows VM and published to the Service.
- Isolation Forest is included as an optional multivariate anomaly layer.

## License

Released under the [MIT License](LICENSE), Copyright (c) 2026 Helios337.
