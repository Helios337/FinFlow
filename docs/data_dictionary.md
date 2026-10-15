# Data Dictionary - FinanceOps360

All monetary amounts are positive except `bank_transactions.amount` (signed:
debit < 0, credit > 0). `injected_error` columns are ground-truth tags for tests
only and are never used by business logic.

| Table | Key columns | Notes |
|---|---|---|
| vendors | vendor_id (PK), vendor_name, country, region, vendor_category, payment_terms_days, currency, status | Master |
| customers | customer_id (PK), customer_type, currency | Master |
| warehouses | warehouse_id (PK), country, city, warehouse_type, capacity_units | Master |
| products | product_id (PK), category, unit_cost, selling_price | Master |
| employees | employee_id (PK), department, manager_id | Master |
| fx_rates | rate_date, from_currency, to_currency, rate | INR base (1 unit from = rate INR) |
| purchase_orders | po_id (PK), vendor_id, warehouse_id, total_amount | PO total = Σ items |
| purchase_order_items | po_item_id, po_id, product_id, quantity, unit_price | |
| vendor_invoices | invoice_id (PK), vendor_id, po_id, due_date, subtotal, tax, total_amount, status | subtotal+tax=total |
| payments | payment_id (PK), invoice_id, payment_date, amount, currency, bank_reference, approval_status | 1:1 to invoice |
| bank_transactions | transaction_id (PK), transaction_type, reference, amount(signed), currency, counterparty | matched by reference |
| customer_invoices | customer_invoice_id (PK), customer_id, subtotal, tax, total_amount, status | Receivables |
| inventory | inventory_id, warehouse_id, product_id, quantity, unit_cost, inventory_value, snapshot_date | Month-end snapshots |
| inventory_movements | movement_id, product_id, source/destination_warehouse, quantity, unit_cost, movement_type, movement_date | Event ledger |
| expenses | expense_id, employee_id, category, amount, approval_status | |
| reconciliation_results | invoice_id, payment_id, bank_reference, status, confidence, amount_diff | Engine output |
| anomalies | transaction_id, source_table, anomaly_type, score, severity, reason | Engine output |
| controls_violations | rule_id, entity_type, entity_id, severity, description | Engine output |

## Injected error catalogue
duplicate_invoice, missing_payment, amount_mismatch (overpayment), currency_mismatch,
timing_diff (120–180d late), wrong_vendor_mapping, duplicate_bank, inventory_mismatch,
unusual_txn. Rates in `config.ERROR_RATES`.
