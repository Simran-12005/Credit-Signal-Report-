-- Credit Signal Report — Phase 2: cache + log every (paid) GST API call.
-- These APIs are paid and rate-limited, so we cache responses per GSTIN and record
-- every call (cache hit or live) with its cost, for cost control and auditing.

-- Cached GST responses, shared across suppliers (GST data is public, so one fetch
-- serves everyone). Keyed by (gstin, provider); refreshed when expired.
CREATE TABLE IF NOT EXISTS csr_gst_cache (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gstin       VARCHAR(15) NOT NULL,
    provider    VARCHAR(30) NOT NULL,
    identity    JSONB,
    compliance  JSONB,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_csr_gst_cache_gstin_provider UNIQUE (gstin, provider)
);

CREATE INDEX IF NOT EXISTS ix_csr_gst_cache_lookup ON csr_gst_cache(gstin, provider);

-- One row per GST lookup attempt (who, which GSTIN, provider, hit-or-live, cost).
CREATE TABLE IF NOT EXISTS csr_gst_api_calls (
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

CREATE INDEX IF NOT EXISTS ix_csr_gst_api_calls_supplier ON csr_gst_api_calls(supplier_id, created_at);
