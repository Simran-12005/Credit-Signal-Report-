-- Credit Signal Report — Phase 1: payment history (the outcome label).
-- A supplier records its own buyers and their orders/invoices, marks them paid,
-- and flags bounces. These first-party signals are the most valuable data we have.

-- Buyers = the supplier's customers. Optionally carry a GSTIN so payment history
-- can later be joined to credit reports for the same GSTIN.
CREATE TABLE IF NOT EXISTS csr_buyers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID NOT NULL REFERENCES csr_suppliers(id) ON DELETE CASCADE,
    gstin       VARCHAR(15),
    name        VARCHAR(200) NOT NULL,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- A supplier can't have the same buyer GSTIN twice (NULL gstins are allowed many).
    CONSTRAINT uq_csr_buyer_supplier_gstin UNIQUE (supplier_id, gstin)
);

CREATE INDEX IF NOT EXISTS ix_csr_buyers_supplier       ON csr_buyers(supplier_id);
CREATE INDEX IF NOT EXISTS ix_csr_buyers_supplier_gstin ON csr_buyers(supplier_id, gstin);

-- Orders / invoices. Payment behaviour is derived from due_date vs paid_date and
-- bounce_count. 'overdue' is NOT stored — it's computed (pending + due_date < today).
CREATE TABLE IF NOT EXISTS csr_orders (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id    UUID NOT NULL REFERENCES csr_suppliers(id) ON DELETE CASCADE,
    buyer_id       UUID NOT NULL REFERENCES csr_buyers(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50),
    amount         NUMERIC(14, 2) NOT NULL,
    order_date     DATE NOT NULL,
    due_date       DATE NOT NULL,
    paid_date      DATE,
    status         VARCHAR(20) NOT NULL DEFAULT 'pending',
    bounce_count   INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_csr_orders_status CHECK (status IN ('pending', 'paid', 'bounced')),
    CONSTRAINT ck_csr_orders_amount_positive CHECK (amount >= 0)
);

CREATE INDEX IF NOT EXISTS ix_csr_orders_buyer    ON csr_orders(buyer_id);
CREATE INDEX IF NOT EXISTS ix_csr_orders_supplier ON csr_orders(supplier_id);
CREATE INDEX IF NOT EXISTS ix_csr_orders_status   ON csr_orders(buyer_id, status);
