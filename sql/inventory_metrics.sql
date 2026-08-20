-- ============================================================================
-- Inventory & anomaly queries
-- ============================================================================

-- 26. Inventory value by warehouse
SELECT warehouse_id, SUM(inventory_value) AS value_inr
FROM inventory GROUP BY warehouse_id ORDER BY value_inr DESC;

-- 27. Inventory by country (via warehouse)
SELECT w.country, SUM(i.inventory_value) AS value_inr
FROM inventory i JOIN warehouses w ON w.warehouse_id = i.warehouse_id
GROUP BY w.country ORDER BY value_inr DESC;

-- 28. Inventory by product category
SELECT p.category, SUM(i.inventory_value) AS value_inr
FROM inventory i JOIN products p ON p.product_id = i.product_id
GROUP BY p.category ORDER BY value_inr DESC;

-- 29. Low-stock SKUs (below safety stock)
SELECT warehouse_id, product_id, quantity
FROM inventory WHERE quantity < 50
ORDER BY quantity ASC LIMIT 50;

-- 30. Overstock SKUs (top 10% quantity per product)
SELECT i.warehouse_id, i.product_id, i.quantity
FROM inventory i
WHERE i.quantity > (SELECT 2*AVG(quantity) FROM inventory i2 WHERE i2.product_id = i.product_id)
ORDER BY i.quantity DESC LIMIT 50;

-- 31. Warehouse utilization vs capacity
SELECT i.warehouse_id, w.capacity_units,
       SUM(i.inventory_value) AS value_inr,
       ROUND(100.0*SUM(i.inventory_value)/NULLIF(w.capacity_units,0),2) AS util_pct
FROM inventory i JOIN warehouses w ON w.warehouse_id = i.warehouse_id
GROUP BY i.warehouse_id, w.capacity_units ORDER BY util_pct DESC;

-- 32. Inventory movement summary by type
SELECT movement_type, COUNT(*) AS moves, SUM(quantity) AS total_qty
FROM inventory_movements GROUP BY movement_type ORDER BY 2 DESC;

-- 33. Inventory reconciliation violations (C5)
SELECT entity_id, description FROM controls_violations WHERE rule_id = 'C5';

-- 34. Anomalies by type and severity
SELECT anomaly_type, severity, COUNT(*) FROM anomalies GROUP BY anomaly_type, severity ORDER BY 3 DESC;

-- 35. High-severity anomalies
SELECT transaction_id, source_table, anomaly_type, score, reason
FROM anomalies WHERE severity = 'HIGH' ORDER BY score DESC LIMIT 50;

-- 36. Unusual bank transactions (z-score)
SELECT transaction_id, observed_value, score
FROM anomalies WHERE anomaly_type = 'unusual_amount' ORDER BY score DESC LIMIT 30;

-- 37. Vendor baseline exceedances
SELECT transaction_id, expected_value, observed_value, score
FROM anomalies WHERE anomaly_type = 'vendor_baseline_exceed' ORDER BY score DESC LIMIT 30;

-- 38. Top discrepancies by vendor with anomaly flag
SELECT vi.vendor_id, COUNT(*) AS recon_issues, COUNT(a.transaction_id) AS anomalies
FROM reconciliation_results r
JOIN vendor_invoices vi ON vi.invoice_id = r.invoice_id
LEFT JOIN anomalies a ON a.transaction_id = r.invoice_id
WHERE r.status NOT IN ('MATCHED','PARTIAL_PAYMENT')
GROUP BY vi.vendor_id ORDER BY recon_issues DESC LIMIT 15;

-- 39. Monthly payable trend
SELECT DATE_TRUNC('month', invoice_date) AS mon, SUM(total_inr) AS payables_inr
FROM v_vendor_invoices_inr GROUP BY 1 ORDER BY 1;

-- 40. Expense by category
SELECT category, SUM(amount) AS total FROM expenses GROUP BY category ORDER BY total DESC;

-- 41. Customer receivables by type
SELECT c.customer_type, SUM(ci.total_amount) AS receivables
FROM customer_invoices ci JOIN customers c ON c.customer_id = ci.customer_id
WHERE ci.status <> 'Paid' GROUP BY c.customer_type ORDER BY receivables DESC;

-- 42. Payment method distribution
SELECT payment_method, COUNT(*) FROM payments GROUP BY payment_method ORDER BY 2 DESC;
