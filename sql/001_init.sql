-- Credit Signal Report — Phase 0 foundation schema.
-- Standalone app: its own database (credit_signal_report). All tables prefixed csr_.
-- Run with:  py scripts/init_db.py   (or psql -f sql/001_init.sql)

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()

-- Suppliers = tenants. All data is scoped to a supplier.
CREATE TABLE IF NOT EXISTS csr_suppliers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- API keys authenticate a supplier. Only the SHA-256 hash is stored; the plaintext
-- key is shown once at creation.
CREATE TABLE IF NOT EXISTS csr_api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id  UUID NOT NULL REFERENCES csr_suppliers(id) ON DELETE CASCADE,
    key_prefix   VARCHAR(16) NOT NULL,
    key_hash     VARCHAR(64) NOT NULL UNIQUE,
    label        VARCHAR(100),
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_csr_api_keys_supplier ON csr_api_keys(supplier_id);

-- Credit signal reports. One row per (supplier, GSTIN lookup).
CREATE TABLE IF NOT EXISTS csr_reports (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id    UUID NOT NULL REFERENCES csr_suppliers(id) ON DELETE CASCADE,
    gstin          VARCHAR(15) NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'pending',
    provider       VARCHAR(30),
    gst_identity   JSONB,
    gst_compliance JSONB,
    error          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_csr_reports_status CHECK (status IN ('pending', 'ready', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_csr_reports_supplier        ON csr_reports(supplier_id);
CREATE INDEX IF NOT EXISTS ix_csr_reports_supplier_gstin  ON csr_reports(supplier_id, gstin);
