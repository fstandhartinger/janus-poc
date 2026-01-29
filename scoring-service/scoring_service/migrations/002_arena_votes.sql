CREATE TABLE arena_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    prompt_id VARCHAR(100) NOT NULL,
    prompt_hash VARCHAR(64),
    model_a VARCHAR(100) NOT NULL,
    model_b VARCHAR(100) NOT NULL,
    winner VARCHAR(20) NOT NULL,
    user_id VARCHAR(100)
);

CREATE UNIQUE INDEX idx_arena_votes_prompt_id ON arena_votes(prompt_id);
CREATE INDEX idx_arena_votes_user_id ON arena_votes(user_id);
CREATE INDEX idx_arena_votes_created_at ON arena_votes(created_at DESC);
