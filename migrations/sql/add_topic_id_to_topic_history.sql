-- Align topic_history with models.py by adding optional topic_id linkage.
-- Safe to run multiple times.

ALTER TABLE topic_history
ADD COLUMN IF NOT EXISTS topic_id INTEGER;

-- Backfill topic_id from topic names per user when possible.
UPDATE topic_history AS th
SET topic_id = t.id
FROM topic AS t
WHERE th.topic_id IS NULL
  AND th.user_id = t.user_id
  AND LOWER(t.name) = LOWER(th.topic);

CREATE INDEX IF NOT EXISTS ix_topic_history_topic_id
ON topic_history (topic_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_topic_history_topic_id_topic'
    ) THEN
        ALTER TABLE topic_history
        ADD CONSTRAINT fk_topic_history_topic_id_topic
        FOREIGN KEY (topic_id)
        REFERENCES topic (id)
        ON DELETE SET NULL;
    END IF;
END $$;
