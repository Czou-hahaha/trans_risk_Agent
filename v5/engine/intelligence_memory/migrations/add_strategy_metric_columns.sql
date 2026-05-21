-- Add strategy tradeoff columns to existing risk_intelligence.stored_findings

ALTER TABLE stored_findings
    ADD COLUMN IF NOT EXISTS approval_delta_pp DOUBLE PRECISION;

ALTER TABLE stored_findings
    ADD COLUMN IF NOT EXISTS volume_delta_pct DOUBLE PRECISION;
