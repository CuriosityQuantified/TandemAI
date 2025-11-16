-- Migration 003: User Threads Table
-- Purpose: Enable multi-conversation management with thread listing and metadata
-- Created: 2025-11-04
-- Dependencies: LangGraph checkpointer tables (from AsyncPostgresSaver)

-- Create user_threads table for conversation metadata
CREATE TABLE IF NOT EXISTS user_threads (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    thread_id TEXT NOT NULL UNIQUE,
    thread_title TEXT DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_archived BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',

    -- Constraints
    CONSTRAINT unique_user_thread UNIQUE(user_id, thread_id)
);

-- Index for fast user-based queries (most common access pattern)
CREATE INDEX IF NOT EXISTS idx_user_threads_user_updated
ON user_threads(user_id, updated_at DESC);

-- Index for filtering archived threads
CREATE INDEX IF NOT EXISTS idx_user_threads_archived
ON user_threads(is_archived)
WHERE NOT is_archived;

-- Index for thread_id lookups (used when loading specific conversations)
CREATE INDEX IF NOT EXISTS idx_user_threads_thread_id
ON user_threads(thread_id);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_threads_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at on modifications
DROP TRIGGER IF EXISTS update_user_threads_timestamp_trigger ON user_threads;
CREATE TRIGGER update_user_threads_timestamp_trigger
BEFORE UPDATE ON user_threads
FOR EACH ROW
EXECUTE FUNCTION update_user_threads_timestamp();

-- Insert default thread for existing sessions (migration safety)
-- This ensures any existing checkpoints have a corresponding thread entry
INSERT INTO user_threads (user_id, thread_id, thread_title, created_at)
SELECT
    'anonymous' AS user_id,
    thread_id,
    'Existing Conversation' AS thread_title,
    NOW() AS created_at
FROM (
    SELECT DISTINCT thread_id::text
    FROM checkpoints
    WHERE thread_id IS NOT NULL
    LIMIT 100  -- Limit to prevent massive migrations
) AS existing_threads
ON CONFLICT (thread_id) DO NOTHING;

-- Verification query (run after migration to confirm)
-- SELECT COUNT(*) as total_threads,
--        COUNT(*) FILTER (WHERE is_archived = false) as active_threads,
--        MAX(updated_at) as most_recent_activity
-- FROM user_threads;
