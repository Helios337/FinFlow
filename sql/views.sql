-- ============================================================================
-- FinanceOps360 :: Analytical VIEWS (run after data load)
-- INR is the reporting currency. fx_rates converts non-INR amounts to INR.
-- ============================================================================

-- Daily INR rate lookup (from_currency -> INR)
CREATE OR REPLACE VIEW v_fx_inr AS
SELECT rate_date, from_currency, rate AS rate_to_inr
FROM fx_rates
WHERE to_currency = 'INR';

-- Invoice amount in INR
CREATE OR REPLACE VIEW v_vendor_invoices_inr AS
SELECT vi.*,
       COALESCE(vi.total_amount * f.rate_to_inr, vi.total_amount) AS total_inr
FROM vendor_invoices vi
LEFT JOIN v_fx_inr f
  ON f.from_currency = vi.currency
 AND f.rate_date = vi.invoice_date;

-- Accounts payable aging (days past due as of dataset end)
CREATE OR REPLACE VIEW v_ap_aging AS
SELECT
    vendor_id,
    invoice_id,
    due_date,
    total_inr,
    CASE
        WHEN due_date >= '2024-12-31' THEN 'Current'
        WHEN '2024-12-31' - due_date <= 30 THEN '1-30'
        WHEN '2024-12-31' - due_date <= 60 THEN '31-60'
        WHEN '2024-12-31' - due_date <= 90 THEN '61-90'
        ELSE '90+'
    END AS aging_bucket
FROM v_vendor_invoices_inr;

-- Reconciliation summary
CREATE OR REPLACE VIEW v_reconciliation_summary AS
SELECT status, COUNT(*) AS cnt, SUM(amount_diff) AS total_diff
FROM reconciliation_results
GROUP BY status;

-- Inventory valuation in INR
CREATE OR REPLACE VIEW v_inventory_valuation AS
SELECT warehouse_id, product_id, snapshot_date,
       quantity, unit_cost, inventory_value,
       inventory_value AS value_inr
FROM inventory;

-- Vendor spend concentration
CREATE OR REPLACE VIEW v_vendor_spend AS
SELECT vendor_id, SUM(total_inr) AS total_spend
FROM v_vendor_invoices_inr
GROUP BY vendor_id;
