-- ============================================================================
-- seed.sql
-- Raw data is loaded from CSVs by python/db_loader.py (pandas to_sql).
-- This file is intentionally minimal; it documents the load contract and
-- re-applies indexes after a bulk load if needed.
-- ============================================================================

-- Re-apply indexes (idempotent)
CREATE INDEX IF NOT EXISTS ix_vendor_invoices_vendor   ON vendor_invoices(vendor_id, status);
CREATE INDEX IF NOT EXISTS ix_vendor_invoices_due      ON vendor_invoices(due_date);
CREATE INDEX IF NOT EXISTS ix_payments_invoice         ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS ix_bank_reference           ON bank_transactions(reference);
CREATE INDEX IF NOT EXISTS ix_inventory_wh_prod        ON inventory(warehouse_id, product_id, snapshot_date);
