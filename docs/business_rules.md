# Business Rules & Reconciliation Methodology

## Three-way matching
invoice → payment (by invoice_id) → bank (by payment.bank_reference).
Bank transactions are signed: debits negative, credits positive.

## Status priority (mutually exclusive)
1. **DUPLICATE** - cloned invoice id (`-D`) or identical vendor+amount.
2. **CURRENCY_MISMATCH** - payment currency ≠ invoice currency.
3. **AMOUNT_MISMATCH** - payment > invoice total + tolerance (overpayment).
4. **MISSING_BANK_TRANSACTION** - payment has no bank debit by reference.
5. **PARTIAL_PAYMENT** - payment < invoice total − tolerance.
6. **MATCHED** - fully matched within tolerance.
7. **MISSING_PAYMENT** - invoice has no payment record.

Tolerance: `max(0.5% of invoice total, 0.01)`.

## Controls
- **C1 Duplicate invoice**: same vendor + same amount.
- **C2 Payment authorization**: amount > 5,000,000 INR and approval_status ≠ Approved.
- **C3 Invoice ≤ PO**: invoice total ≤ linked PO total.
- **C4 Payment ≤ invoice**: payment amount ≤ invoice total.
- **C5 Inventory identity**: net movements up to snapshot date = snapshot quantity.
- **C6 Late payment**: payment date > terms + 30 days.
- **C7 Wrong counterparty**: bank counterparty ≠ vendor name (fuzzy ratio < 0.6).
- **C8 Duplicate bank**: same reference + amount + transaction type.

## Anomaly methods (explainable)
- Z-score on bank debit magnitudes (> 3σ → unusual).
- IQR on invoice amounts (outside 1.5×IQR).
- Vendor baseline (invoice > vendor mean + 3σ).
- Optional Isolation Forest for multivariate detection.

## FX
All non-INR amounts converted to INR using `fx_rates` (daily, INR base) before
aggregation. View `v_vendor_invoices_inr` provides `total_inr`.
