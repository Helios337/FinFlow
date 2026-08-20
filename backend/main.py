"""FastAPI application for FinanceOps360."""
from __future__ import annotations
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))

from backend import services  # noqa: E402
from backend.schemas import (  # noqa: E402
    Vendor, Invoice, Payment, Transaction, InventoryRow, ReconciliationRow,
    Anomaly, Metrics, AIQuestion, AIAnswer,
)

app = FastAPI(title="FinanceOps360 API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/vendors", response_model=list[Vendor])
def vendors(limit: int = 200):
    return services.get_vendors(limit)


@app.get("/invoices", response_model=list[Invoice])
def invoices(status: str | None = None, limit: int = 200):
    return services.get_invoices(status, limit)


@app.get("/payments", response_model=list[Payment])
def payments(limit: int = 200):
    return services.get_payments(limit)


@app.get("/transactions", response_model=list[Transaction])
def transactions(limit: int = 200):
    return services.get_transactions(limit)


@app.get("/inventory", response_model=list[InventoryRow])
def inventory(limit: int = 200):
    return services.get_inventory(limit)


@app.get("/reconciliation", response_model=list[ReconciliationRow])
def reconciliation(status: str | None = None, limit: int = 500):
    return services.get_reconciliation(status, limit)


@app.get("/anomalies", response_model=list[Anomaly])
def anomalies(severity: str | None = None, limit: int = 200):
    return services.get_anomalies(severity, limit)


@app.get("/controls")
def controls(limit: int = 500):
    return services.get_controls(limit)


@app.get("/metrics", response_model=Metrics)
def metrics():
    return services.get_metrics()


@app.post("/ai/ask", response_model=AIAnswer)
async def ai_ask(q: AIQuestion):
    from backend.ai.copilot import ask
    return await ask(q.question)
