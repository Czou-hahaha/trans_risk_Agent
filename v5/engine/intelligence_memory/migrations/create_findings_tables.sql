-- Risk Intelligence Storage Layer — structured findings persistence
-- Database: risk_intelligence

CREATE TABLE IF NOT EXISTS stored_findings (
    finding_id VARCHAR(64) PRIMARY KEY,
    investigation_id VARCHAR(64) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,
    finding_type VARCHAR(32) NOT NULL,
    dimension_name VARCHAR(128),
    dimension_value VARCHAR(256),
    summary TEXT NOT NULL,
    severity VARCHAR(16),
    contribution_pp DOUBLE PRECISION,
    delta_pp DOUBLE PRECISION,
    approval_delta_pp DOUBLE PRECISION,
    volume_delta_pct DOUBLE PRECISION,
    generated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_stored_findings_investigation_id
    ON stored_findings (investigation_id);

CREATE INDEX IF NOT EXISTS ix_stored_findings_metric_name
    ON stored_findings (metric_name);

CREATE INDEX IF NOT EXISTS ix_stored_findings_dimension
    ON stored_findings (dimension_name, dimension_value);

CREATE TABLE IF NOT EXISTS investigation_snapshots (
    investigation_id VARCHAR(64) PRIMARY KEY,
    metric_name VARCHAR(64) NOT NULL,
    analysis_date DATE NOT NULL,
    workflow_status VARCHAR(32) NOT NULL,
    findings_count INTEGER NOT NULL DEFAULT 0,
    needs_investigation BOOLEAN,
    trigger_reason TEXT,
    generated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_investigation_snapshots_metric_name
    ON investigation_snapshots (metric_name);
