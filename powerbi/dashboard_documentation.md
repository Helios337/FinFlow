# Power BI - Dashboard Documentation

Author the model in **Power BI Desktop** (Windows VM/Parallels), then publish
to **Power BI Service (free)**. Connect to PostgreSQL via the Postgres connector
(server `localhost`, port `5433` from host / service name `postgres` from
Docker network, database `financeops`, read-only user).

## Data model (star schema)
**Facts**: `FactVendorInvoices` (vendor_invoices + v_vendor_invoices_inr),
`FactPayments` (payments), `FactBankTransactions` (bank_transactions),
`FactInventory` (inventory), `FactExpenses` (expenses),
`FactCustomerInvoices` (customer_invoices).
**Dimensions**: DimDate, DimVendor, DimCustomer, DimProduct, DimWarehouse,
DimEmployee, DimCurrency (fx_rates).

## DAX measures
Total Payables, Total Receivables, Total Revenue, Total Expenses, Outstanding
Amount, Overdue Amount, Payment Rate, On-Time Payment %, Avg Payment Delay,
Inventory Value (INR via fx_rates), Mismatch Rate, Inventory Turnover (proxy).

## Dashboards
1. **Executive Finance** - revenue/expense/payables/receivables trends, vendor
   spend, payment aging, reconciliation status.
2. **Reconciliation** - matched/unmatched/mismatched/duplicate counts, mismatch
   value, vendor-wise discrepancies, top discrepancies table.
3. **Supply Chain** - inventory by warehouse/country/category, low-stock &
   overstock products, warehouse utilization, inventory movement.
4. **Accounts Payable** - outstanding payable, vendor aging (Current/1–30/
   31–60/61–90/90+), overdue, vendor concentration, payment delays.

## Build notes
- `v_vendor_invoices_inr` provides `total_inr` for currency-consistent totals.
- Schedule refresh in Service; keep the Postgres source reachable.
- Place screenshots in `powerbi/screenshots/`.
