-- Credit Signal Report — Phase 3: MCA (company / directors / charges) + legal data.
-- Same cache+log pattern as GST (Phase 2): these lookups are paid and slow-changing,
-- so we cache per (gstin, provider) and record every call with its cost.

-- Cached MCA + legal responses, shared across suppliers (this data is public).
CREATE TABLE IF NOT EXISTS csr_mca_cache (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gstin       VARCHAR(15) NOT NULL,
    provider    VARCHAR(30) NOT NULL,
    company     JSONB,   -- incorporation, age, status, capital, RoC
    directors   JSONB,   -- count + roster + disqualification flag
    charges     JSONB,   -- secured loans (open/satisfied) registered against the company
    legal       JSONB,   -- insolvency (IBBI) + recovery (NJDG) cases
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_csr_mca_cache_gstin_provider UNIQUE (gstin, provider)
);

CREATE INDEX IF NOT EXISTS ix_csr_mca_cache_lookup ON csr_mca_cache(gstin, provider);

-- One row per MCA lookup attempt (who, which GSTIN, provider, hit-or-live, cost).
CREATE TABLE IF NOT EXISTS csr_mca_api_calls (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID NOT NULL REFERENCES csr_suppliers(id) ON DELETE CASCADE,
    gstin       VARCHAR(15) NOT NULL,
    provider    VARCHAR(30) NOT NULL,
    cache_hit   BOOLEAN NOT NULL DEFAULT FALSE,
    success     BOOLEAN NOT NULL DEFAULT TRUE,
    cost        NUMERIC(10, 4) NOT NULL DEFAULT 0,
    latency_ms  INTEGER,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_csr_mca_api_calls_supplier ON csr_mca_api_calls(supplier_id, created_at);

-- The report now carries the MCA + legal signal groups alongside GST (nullable until
-- fetched; missing data never breaks the report).
ALTER TABLE csr_reports ADD COLUMN IF NOT EXISTS mca_provider  VARCHAR(30);
ALTER TABLE csr_reports ADD COLUMN IF NOT EXISTS mca_company   JSONB;
ALTER TABLE csr_reports ADD COLUMN IF NOT EXISTS mca_directors JSONB;
ALTER TABLE csr_reports ADD COLUMN IF NOT EXISTS mca_charges   JSONB;
ALTER TABLE csr_reports ADD COLUMN IF NOT EXISTS mca_legal     JSONB;
