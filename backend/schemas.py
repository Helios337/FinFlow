"""Pydantic schemas."""
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Any


class Vendor(BaseModel):
    vendor_id: str
    vendor_name: str
    country: Optional[str] = None
    region: Optional[str] = None
    vendor_category: Optional[str] = None
    payment_terms_days: Optional[int] = None
    currency: Optional[str] = None
    status: Optional[str] = None


class Invoice(BaseModel):
    invoice_id: str
    vendor_id: Optional[str] = None
    po_id: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    status: Optional[str] = None


class Payment(BaseModel):
    payment_id: str
    invoice_id: Optional[str] = None
    payment_date: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    bank_reference: Optional[str] = None
    payment_method: Optional[str] = None
    approval_status: Optional[str] = None


class Transaction(BaseModel):
    transaction_id: str
    transaction_date: Optional[str] = None
    transaction_type: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    counterparty: Optional[str] = None


class InventoryRow(BaseModel):
    warehouse_id: Optional[str] = None
    product_id: Optional[str] = None
    quantity: Optional[int] = None
    unit_cost: Optional[float] = None
    inventory_value: Optional[float] = None
    snapshot_date: Optional[str] = None


class ReconciliationRow(BaseModel):
    invoice_id: Optional[str] = None
    payment_id: Optional[str] = None
    bank_reference: Optional[str] = None
    status: str
    confidence: Optional[float] = None
    amount_diff: Optional[float] = None
    currency_match: Optional[bool] = None


class Anomaly(BaseModel):
    transaction_id: Optional[str] = None
    source_table: Optional[str] = None
    anomaly_type: Optional[str] = None
    score: Optional[float] = None
    severity: Optional[str] = None
    reason: Optional[str] = None
    expected_value: Optional[float] = None
    observed_value: Optional[float] = None
    recommended_action: Optional[str] = None


class Metrics(BaseModel):
    total_payables_inr: Optional[float] = None
    total_receivables_inr: Optional[float] = None
    outstanding_invoices: Optional[int] = None
    matched: Optional[int] = None
    mismatched: Optional[int] = None
    duplicates: Optional[int] = None
    anomalies: Optional[int] = None
    match_rate_pct: Optional[float] = None


class AIQuestion(BaseModel):
    question: str


class AIAnswer(BaseModel):
    question: str
    sql: Optional[str] = None
    columns: list[str] = []
    rows: list[dict] = []
    explanation: Optional[str] = None
    error: Optional[str] = None
