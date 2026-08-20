-- ============================================================================
-- Reconciliation & controls queries
-- ============================================================================

-- 11. Reconciliation status distribution
SELECT status, COUNT(*) FROM reconciliation_results GROUP BY status ORDER BY 2 DESC;

-- 12. Mismatch value by status
SELECT status, SUM(ABS(amount_diff)) AS abs_diff
FROM reconciliation_results WHERE amount_diff IS NOT NULL GROUP BY status;

-- 13. Invoice <-> Payment <-> Bank exact matches
SELECT r.invoice_id, r.payment_id, r.bank_reference, r.status
FROM reconciliation_results r WHERE r.status = 'MATCHED';

-- 14. Amount mismatches with vendor
SELECT r.invoice_id, vi.vendor_id, r.amount_diff
FROM reconciliation_results r JOIN vendor_invoices vi ON vi.invoice_id = r.invoice_id
WHERE r.status = 'AMOUNT_MISMATCH';

-- 15. Missing payments (no payment record)
SELECT r.invoice_id, vi.vendor_id, vi.total_inr
FROM reconciliation_results r JOIN v_vendor_invoices_inr vi ON vi.invoice_id = r.invoice_id
WHERE r.status = 'MISSING_PAYMENT';

-- 16. Missing bank transaction
SELECT r.invoice_id, r.payment_id FROM reconciliation_results r WHERE r.status = 'MISSING_BANK_TRANSACTION';

-- 17. Currency mismatches
SELECT r.invoice_id, vi.currency AS inv_cur, p.currency AS pay_cur
FROM reconciliation_results r
JOIN vendor_invoices vi ON vi.invoice_id = r.invoice_id
JOIN payments p ON p.payment_id = r.payment_id
WHERE r.status = 'CURRENCY_MISMATCH';

-- 18. Duplicate invoices (same vendor + amount)
SELECT vendor_id, total_amount, COUNT(*) AS cnt
FROM vendor_invoices GROUP BY vendor_id, total_amount HAVING COUNT(*) > 1;

-- 19. Vendor-wise discrepancy counts
SELECT vi.vendor_id, COUNT(*) AS discrepancies
FROM reconciliation_results r JOIN vendor_invoices vi ON vi.invoice_id = r.invoice_id
WHERE r.status NOT IN ('MATCHED','PARTIAL_PAYMENT')
GROUP BY vi.vendor_id ORDER BY discrepancies DESC LIMIT 15;

-- 20. Control violations by rule
SELECT rule_id, severity, COUNT(*) FROM controls_violations GROUP BY rule_id, severity ORDER BY 2 DESC;

-- 21. Largest mismatch transactions
SELECT r.invoice_id, ABS(r.amount_diff) AS diff
FROM reconciliation_results r WHERE r.amount_diff IS NOT NULL
ORDER BY diff DESC LIMIT 20;

-- 22. Payment authorization breaches (C2)
SELECT entity_id, description FROM controls_violations WHERE rule_id = 'C2';

-- 23. Bank counterparty mismatches (C7)
SELECT entity_id, description FROM controls_violations WHERE rule_id = 'C7';

-- 24. Duplicate bank transactions (C8)
SELECT entity_id, description FROM controls_violations WHERE rule_id = 'C8';

-- 25. Reconciliation rate
SELECT ROUND(100.0*SUM(CASE WHEN status='MATCHED' THEN 1 ELSE 0 END)/COUNT(*),2) AS match_rate
FROM reconciliation_results;
