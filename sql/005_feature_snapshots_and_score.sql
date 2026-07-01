-- Credit Signal Report — Phase 4: clean, ML-ready feature dataset + rule-based score.
-- One row per (supplier, business) build: all collected signals flattened into `features`,
-- the payment outcome as `label`, plus the rule-based score/band/breakdown. Versioned and
-- stamped with `as_of_date` so the dataset is reproducible as data grows.

CREATE TABLE IF NOT EXISTS csr_feature_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id     UUID NOT NULL REFERENCES csr_suppliers(id) ON DELETE CASCADE,
    gstin           VARCHAR(15) NOT NULL,
    -- The buyer whose first-party payment history supplied the label (if any).
    buyer_id        UUID REFERENCES csr_buyers(id) ON DELETE SET NULL,
    as_of_date      DATE NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    features        JSONB NOT NULL,           -- flattened signal features
    label           JSONB,                    -- payment outcome (null until we have orders)
    has_label       BOOLEAN NOT NULL DEFAULT FALSE,
    score           NUMERIC(5, 2),            -- rule-based score 0–100
    risk_band       VARCHAR(10),              -- Low | Medium | High | Unknown
    score_breakdown JSONB,
    gst_provider    VARCHAR(30),
    mca_provider    VARCHAR(30),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- One row per (supplier, business, version); versions accrue as data is rebuilt.
    CONSTRAINT uq_csr_feature_snapshot_version UNIQUE (supplier_id, gstin, version)
);

CREATE INDEX IF NOT EXISTS ix_csr_feature_snapshots_supplier ON csr_feature_snapshots(supplier_id, created_at);
CREATE INDEX IF NOT EXISTS ix_csr_feature_snapshots_gstin    ON csr_feature_snapshots(supplier_id, gstin);

-- The rule-based score is also attached to each report (so a bare GSTIN lookup is
-- immediately usable). Added here since Phase 4 introduces scoring.
ALTER TABLE csr_reports ADD COLUMN IF NOT EXISTS score           NUMERIC(5, 2);
ALTER TABLE csr_reports ADD COLUMN IF NOT EXISTS risk_band       VARCHAR(10);
ALTER TABLE csr_reports ADD COLUMN IF NOT EXISTS score_breakdown JSONB;
