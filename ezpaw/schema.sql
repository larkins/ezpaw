CREATE TABLE IF NOT EXISTS gpaw_runs (
    id              SERIAL PRIMARY KEY,
    script_name     TEXT NOT NULL,
    arguments       JSONB,
    started_at      TIMESTAMP WITH TIME ZONE,
    finished_at        TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,
    status          TEXT DEFAULT 'running',
    results         JSONB,
    ks_gap          FLOAT,
    qp_gap          FLOAT,
    dxc             FLOAT,
    stdout_path     TEXT,
    stderr_path     TEXT,
    error_message   TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gpaw_runs_status ON gpaw_runs(status);
CREATE INDEX IF NOT EXISTS idx_gpaw_runs_started_at ON gpaw_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_gpaw_runs_script_name ON gpaw_runs(script_name);