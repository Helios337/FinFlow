-- ============================================================================
-- FinanceOps360 :: PostgreSQL schema
-- Reporting currency: INR (base). All non-bank monetary amounts are positive.
-- bank_transactions.amount uses a SIGNED convention (debit < 0, credit > 0).
-- `injected_error` columns are GROUND-TRUTH tags for tests only; the
-- reconciliation/controls logic never reads them.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Master / dimension tables
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id          VARCHAR(20) PRIMARY KEY,
    vendor_name        TEXT NOT NULL,
    country            VARCHAR(60),
    region             VARCHAR(40),
    vendor_category    VARCHAR(40),
    payment_terms_days INTEGER DEFAULT 30,
    currency           VARCHAR(10) DEFAULT 'INR',
    status             VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id     VARCHAR(20) PRIMARY KEY,
    customer_name   TEXT NOT NULL,
    country         VARCHAR(60),
    region          VARCHAR(40),
    customer_type   VARCHAR(40),
    currency        VARCHAR(10) DEFAULT 'INR',
    status          VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id    VARCHAR(20) PRIMARY KEY,
    warehouse_name  TEXT NOT NULL,
    country         VARCHAR(60),
    city            VARCHAR(60),
    warehouse_type  VARCHAR(40),
    capacity_units  INTEGER
);

CREATE TABLE IF NOT EXISTS products (
    product_id   VARCHAR(20) PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     VARCHAR(40),
    unit_cost    NUMERIC(14,2) NOT NULL,
    selling_price NUMERIC(14,2) NOT NULL,
    currency     VARCHAR(10) DEFAULT 'INR'
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id   VARCHAR(20) PRIMARY KEY,
    employee_name TEXT NOT NULL,
    department    VARCHAR(40),
    location      VARCHAR(60),
    manager_id    VARCHAR(20) REFERENCES employees(employee_id)
);

-- ---------------------------------------------------------------------------
-- FX rates (INR base). rate = 1 unit of from_currency in to_currency.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fx_rates (
    id            SERIAL PRIMARY KEY,
    rate_date     DATE NOT NULL,
    from_currency VARCHAR(10) NOT NULL,
    to_currency   VARCHAR(10) NOT NULL,
    rate          NUMERIC(14,6) NOT NULL,
    UNIQUE (rate_date, from_currency, to_currency)
);

-- ---------------------------------------------------------------------------
-- Purchasing
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id          VARCHAR(20) PRIMARY KEY,
    vendor_id      VARCHAR(20) REFERENCES vendors(vendor_id),
    po_date        DATE NOT NULL,
    warehouse_id   VARCHAR(20) REFERENCES warehouses(warehouse_id),
    currency       VARCHAR(10) DEFAULT 'INR',
    total_amount   NUMERIC(14,2) NOT NULL,
    status         VARCHAR(20) DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    po_item_id  SERIAL PRIMARY KEY,
    po_id       VARCHAR(20) REFERENCES purchase_orders(po_id),
    product_id  VARCHAR(20) REFERENCES products(product_id),
    quantity    INTEGER NOT NULL,
    unit_price  NUMERIC(14,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS vendor_invoices (
    invoice_id    VARCHAR(20) PRIMARY KEY,
    vendor_id     VARCHAR(20) REFERENCES vendors(vendor_id),
    po_id         VARCHAR(20) REFERENCES purchase_orders(po_id),
    invoice_date  DATE NOT NULL,
    due_date      DATE NOT NULL,
    currency      VARCHAR(10) DEFAULT 'INR',
    subtotal      NUMERIC(14,2) NOT NULL,
    tax           NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_amount  NUMERIC(14,2) NOT NULL,
    status        VARCHAR(20) DEFAULT 'Pending',
    injected_error VARCHAR(40)   -- ground truth only
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id      VARCHAR(20) PRIMARY KEY,
    invoice_id      VARCHAR(20) REFERENCES vendor_invoices(invoice_id),
    payment_date    DATE NOT NULL,
    amount          NUMERIC(14,2) NOT NULL,
    currency        VARCHAR(10) DEFAULT 'INR',
    bank_reference  VARCHAR(60),
    payment_method  VARCHAR(30),
    status          VARCHAR(20) DEFAULT 'completed',
    approval_status VARCHAR(20) DEFAULT 'Approved',
    approved_by     VARCHAR(40),
    injected_error  VARCHAR(40)   -- ground truth only
);

-- Signed bank ledger: debit < 0, credit > 0.
CREATE TABLE IF NOT EXISTS bank_transactions (
    transaction_id   VARCHAR(20) PRIMARY KEY,
    transaction_date DATE NOT NULL,
    transaction_type VARCHAR(20),   -- Credit/Debit/Fee/Refund/Transfer
    description      TEXT,
    reference        VARCHAR(60),
    amount           NUMERIC(16,2) NOT NULL,
    currency         VARCHAR(10) DEFAULT 'INR',
    bank_account     VARCHAR(40),
    counterparty     TEXT,
    injected_error   VARCHAR(40)   -- ground truth only
);

-- ---------------------------------------------------------------------------
-- Receivables
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_invoices (
    customer_invoice_id VARCHAR(20) PRIMARY KEY,
    customer_id         VARCHAR(20) REFERENCES customers(customer_id),
    invoice_date        DATE NOT NULL,
    due_date            DATE NOT NULL,
    currency            VARCHAR(10) DEFAULT 'INR',
    subtotal            NUMERIC(14,2) NOT NULL,
    tax                 NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_amount        NUMERIC(14,2) NOT NULL,
    status              VARCHAR(20) DEFAULT 'Pending'
);

-- ---------------------------------------------------------------------------
-- Inventory
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id   SERIAL PRIMARY KEY,
    warehouse_id   VARCHAR(20) REFERENCES warehouses(warehouse_id),
    product_id     VARCHAR(20) REFERENCES products(product_id),
    quantity       INTEGER NOT NULL,
    unit_cost      NUMERIC(14,2) NOT NULL,
    inventory_value NUMERIC(16,2) NOT NULL,
    snapshot_date  DATE NOT NULL,
    injected_error VARCHAR(40),   -- ground truth only
    UNIQUE (warehouse_id, product_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS inventory_movements (
    movement_id          SERIAL PRIMARY KEY,
    product_id           VARCHAR(20) REFERENCES products(product_id),
    source_warehouse     VARCHAR(20) REFERENCES warehouses(warehouse_id),
    destination_warehouse VARCHAR(20) REFERENCES warehouses(warehouse_id),
    quantity             INTEGER NOT NULL,
    unit_cost            NUMERIC(14,2) NOT NULL,
    movement_date        DATE NOT NULL,
    movement_type        VARCHAR(20),  -- Purchase/Sale/Transfer/Return/Adjustment
    reference            VARCHAR(60)
);

CREATE TABLE IF NOT EXISTS expenses (
    expense_id       VARCHAR(20) PRIMARY KEY,
    employee_id      VARCHAR(20) REFERENCES employees(employee_id),
    expense_date     DATE NOT NULL,
    category         VARCHAR(40),
    amount           NUMERIC(14,2) NOT NULL,
    currency         VARCHAR(10) DEFAULT 'INR',
    approval_status  VARCHAR(20) DEFAULT 'Approved'
);

-- ---------------------------------------------------------------------------
-- Persistence tables (written by Python pipeline; consumed by API / Power BI)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reconciliation_results (
    id              SERIAL PRIMARY KEY,
    invoice_id      VARCHAR(20),
    payment_id      VARCHAR(20),
    bank_reference  VARCHAR(60),
    status          VARCHAR(30) NOT NULL,
    confidence      NUMERIC(5,4),
    amount_diff     NUMERIC(16,2),
    currency_match  BOOLEAN,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS anomalies (
    id                 SERIAL PRIMARY KEY,
    transaction_id     VARCHAR(20),
    source_table       VARCHAR(30),
    anomaly_type       VARCHAR(40),
    score              NUMERIC(8,4),
    severity           VARCHAR(10),
    reason             TEXT,
    expected_value     NUMERIC(16,2),
    observed_value     NUMERIC(16,2),
    recommended_action TEXT
);

CREATE TABLE IF NOT EXISTS controls_violations (
    id           SERIAL PRIMARY KEY,
    rule_id      VARCHAR(20) NOT NULL,
    entity_type  VARCHAR(30),
    entity_id    VARCHAR(40),
    severity     VARCHAR(10),
    description  TEXT,
    detected_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- Indexes (added after load for write performance; declared here for clarity)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_vendor_invoices_vendor   ON vendor_invoices(vendor_id, status);
CREATE INDEX IF NOT EXISTS ix_vendor_invoices_due      ON vendor_invoices(due_date);
CREATE INDEX IF NOT EXISTS ix_payments_invoice         ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS ix_payments_reference       ON payments(bank_reference);
CREATE INDEX IF NOT EXISTS ix_bank_reference           ON bank_transactions(reference);
CREATE INDEX IF NOT EXISTS ix_bank_date                ON bank_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS ix_inventory_wh_prod        ON inventory(warehouse_id, product_id, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_movements_product        ON inventory_movements(product_id, movement_date);
CREATE INDEX IF NOT EXISTS ix_recon_status             ON reconciliation_results(status);
CREATE INDEX IF NOT EXISTS ix_anomalies_type           ON anomalies(anomaly_type, severity);
