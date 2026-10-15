"""Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class Vendor(BaseModel):
    vendor_id: str
    vendor_name: str
    country: str | None = None
    region: str | None = None
    vendor_category: str | None = None
    payment_terms_days: int | None = None
    currency: str | None = None
    status: str | None = None


class Invoice(BaseModel):
    invoice_id: str
    vendor_id: str | None = None
    po_id: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    total_amount: float | None = None
    status: str | None = None


class Payment(BaseModel):
    payment_id: str
    invoice_id: str | None = None
    payment_date: str | None = None
    amount: float | None = None
    currency: str | None = None
    bank_reference: str | None = None
    payment_method: str | None = None
    approval_status: str | None = None


class Transaction(BaseModel):
    transaction_id: str
    transaction_date: str | None = None
    transaction_type: str | None = None
    amount: float | None = None
    currency: str | None = None
    counterparty: str | None = None


class InventoryRow(BaseModel):
    warehouse_id: str | None = None
    product_id: str | None = None
    quantity: int | None = None
    unit_cost: float | None = None
    inventory_value: float | None = None
    snapshot_date: str | None = None


class ReconciliationRow(BaseModel):
    invoice_id: str | None = None
    payment_id: str | None = None
    bank_reference: str | None = None
    status: str
    confidence: float | None = None
    amount_diff: float | None = None
    currency_match: bool | None = None


class Anomaly(BaseModel):
    transaction_id: str | None = None
    source_table: str | None = None
    anomaly_type: str | None = None
    score: float | None = None
    severity: str | None = None
    reason: str | None = None
    expected_value: float | None = None
    observed_value: float | None = None
    recommended_action: str | None = None


class Metrics(BaseModel):
    total_payables_inr: float | None = None
    total_receivables_inr: float | None = None
    outstanding_invoices: int | None = None
    matched: int | None = None
    mismatched: int | None = None
    duplicates: int | None = None
    anomalies: int | None = None
    match_rate_pct: float | None = None


class AIQuestion(BaseModel):
    question: str


class AIAnswer(BaseModel):
    question: str
    sql: str | None = None
    columns: list[str] = []
    rows: list[dict] = []
    explanation: str | None = None
    error: str | None = None
