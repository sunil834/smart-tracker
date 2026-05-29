-- Migration: Add created_at to topic_history
-- Run this SQL directly against your Postgres database or via the provided script.

ALTER TABLE topic_history
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
