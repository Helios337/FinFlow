-- ============================================================================
-- FinanceOps360 :: Finance metric queries (PostgreSQL)
-- Run these in psql / Power BI / notebooks. 40+ queries across the project.
-- ============================================================================

-- 1. Total vendor payables (outstanding) in INR
SELECT SUM(total_inr) AS total_payables_inr
FROM v_vendor_invoices_inr
WHERE invoice_id NOT IN (SELECT invoice_id FROM reconciliation_results WHERE status IN ('MATCHED','PARTIAL_PAYMENT'));

-- 2. Total receivables in INR
SELECT SUM(total_amount * COALESCE(f.rate_to_inr,1)) AS total_receivables_inr
FROM customer_invoices ci
LEFT JOIN v_fx_inr f ON f.from_currency = ci.currency AND f.rate_date = ci.invoice_date
WHERE ci.status <> 'Paid';

-- 3. AP aging bucket counts
SELECT aging_bucket, COUNT(*) AS invoices, SUM(total_inr) AS amount_inr
FROM v_ap_aging GROUP BY aging_bucket ORDER BY aging_bucket;

-- 4. Vendor payable by vendor (top 10)
SELECT vendor_id, SUM(total_inr) AS payable_inr
FROM v_vendor_invoices_inr
WHERE invoice_id NOT IN (SELECT invoice_id FROM reconciliation_results WHERE status IN ('MATCHED','PARTIAL_PAYMENT'))
GROUP BY vendor_id ORDER BY payable_inr DESC LIMIT 10;

-- 5. Vendor concentration (top vendors % of spend)
WITH spend AS (SELECT vendor_id, SUM(total_spend) AS s FROM v_vendor_spend GROUP BY vendor_id),
     tot AS (SELECT SUM(s) AS t FROM spend)
SELECT vendor_id, s, ROUND(100.0*s/t,2) AS pct
FROM spend, tot ORDER BY s DESC LIMIT 10;

-- 6. Monthly expenses + MoM change
SELECT DATE_TRUNC('month', expense_date) AS mon, SUM(amount) AS monthly,
       LAG(SUM(amount)) OVER (ORDER BY DATE_TRUNC('month', expense_date)) AS prev,
       ROUND(100.0*(SUM(amount)-LAG(SUM(amount)) OVER (ORDER BY DATE_TRUNC('month', expense_date)))
             /NULLIF(LAG(SUM(amount)) OVER (ORDER BY DATE_TRUNC('month', expense_date)),0),2) AS mom_pct
FROM expenses GROUP BY 1 ORDER BY 1;

-- 7. Average payment delay (days)
SELECT AVG(p.payment_date - vi.due_date) AS avg_delay_days
FROM payments p JOIN vendor_invoices vi ON vi.invoice_id = p.invoice_id;

-- 8. On-time payment %
SELECT ROUND(100.0*SUM(CASE WHEN p.payment_date <= vi.due_date THEN 1 ELSE 0 END)/COUNT(*),2) AS on_time_pct
FROM payments p JOIN vendor_invoices vi ON vi.invoice_id = p.invoice_id;

-- 9. Overdue invoices count + value
SELECT COUNT(*) AS overdue_cnt, SUM(total_inr) AS overdue_inr
FROM v_ap_aging WHERE aging_bucket = '90+';

-- 10. Invoice-to-PO amount check violations
SELECT vi.invoice_id, vi.total_amount, po.total_amount
FROM vendor_invoices vi JOIN purchase_orders po ON po.po_id = vi.po_id
WHERE vi.total_amount > po.total_amount * 1.001;
