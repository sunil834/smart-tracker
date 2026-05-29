CREATE TABLE IF NOT EXISTS badge (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    tier VARCHAR(32) NOT NULL,
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_badge_user_id ON badge (user_id);
CREATE INDEX IF NOT EXISTS idx_badge_user_tier ON badge (user_id, tier);