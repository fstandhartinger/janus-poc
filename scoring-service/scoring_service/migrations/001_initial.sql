CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Competitors table (optional, for registered competitors)
CREATE TABLE competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    name VARCHAR(200) NOT NULL,
    team VARCHAR(200),
    description TEXT,
    container_image TEXT NOT NULL,
    github_url TEXT,

    -- Best scores (updated after each run)
    best_composite_score DECIMAL(5,4),
    best_run_id UUID,

    -- Status
    verified BOOLEAN DEFAULT FALSE,
    is_baseline BOOLEAN DEFAULT FALSE
);

-- Scoring runs table
CREATE TABLE scoring_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Target
    target_type VARCHAR(50) NOT NULL,
    target_url TEXT,
    container_image TEXT,
    competitor_id UUID REFERENCES competitors(id),

    -- Configuration
    suite VARCHAR(50) NOT NULL DEFAULT 'quick',
    model VARCHAR(100),
    subset_percent INTEGER DEFAULT 100,

    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    progress_current INTEGER DEFAULT 0,
    progress_total INTEGER,

    -- Scores (populated on completion)
    composite_score DECIMAL(5,4),
    quality_score DECIMAL(5,4),
    speed_score DECIMAL(5,4),
    cost_score DECIMAL(5,4),
    streaming_score DECIMAL(5,4),
    multimodal_score DECIMAL(5,4),

    -- Metadata
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT,
    metadata JSONB
);

-- Task results table
CREATE TABLE task_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES scoring_runs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Task info
    task_id VARCHAR(100) NOT NULL,
    benchmark VARCHAR(50) NOT NULL,
    task_type VARCHAR(50),

    -- Result
    success BOOLEAN,
    response_text TEXT,
    error TEXT,

    -- Scores
    quality_score DECIMAL(5,4),

    -- Metrics
    latency_seconds DECIMAL(10,3),
    ttft_seconds DECIMAL(10,3),
    avg_tps DECIMAL(10,2),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(10,6),

    -- Streaming metrics
    continuity_score DECIMAL(5,4),
    max_gap_seconds DECIMAL(10,3),

    -- Full data
    streaming_metrics JSONB,
    metadata JSONB
);

ALTER TABLE competitors
    ADD CONSTRAINT competitors_best_run_id_fkey
    FOREIGN KEY (best_run_id) REFERENCES scoring_runs(id);

-- Indexes
CREATE INDEX idx_scoring_runs_status ON scoring_runs(status);
CREATE INDEX idx_scoring_runs_created_at ON scoring_runs(created_at DESC);
CREATE INDEX idx_scoring_runs_competitor_id ON scoring_runs(competitor_id);
CREATE INDEX idx_task_results_run_id ON task_results(run_id);
CREATE INDEX idx_task_results_benchmark ON task_results(benchmark);
CREATE INDEX idx_competitors_best_score ON competitors(best_composite_score DESC NULLS LAST);
