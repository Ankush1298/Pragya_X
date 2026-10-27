-- 0006: chat-scoped learning layer + notifications. Generated from backend/app/database/learning_schema.py
-- Idempotent, non-destructive. Apply after 0005.
BEGIN;

CREATE TABLE IF NOT EXISTS learning_chats (
        id VARCHAR(64) PRIMARY KEY,
        user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        subject_id VARCHAR(64),
        subject_title TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS idx_learning_chats_user ON learning_chats (user_id, updated_at);

CREATE TABLE IF NOT EXISTS learning_chat_messages (
        id VARCHAR(64) PRIMARY KEY,
        chat_id VARCHAR(64) NOT NULL REFERENCES learning_chats(id) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
        content TEXT NOT NULL,
        suggested_followups TEXT,
        seq INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS idx_learning_chat_messages_chat ON learning_chat_messages (chat_id, created_at);

CREATE TABLE IF NOT EXISTS learning_chat_attempts (
        attempt_id VARCHAR(64) PRIMARY KEY REFERENCES assessment_attempts(id) ON DELETE CASCADE,
        chat_id VARCHAR(64) NOT NULL REFERENCES learning_chats(id) ON DELETE CASCADE,
        kind TEXT NOT NULL CHECK (kind IN ('diagnostic', 'reassessment')),
        seq INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS idx_learning_chat_attempts_chat ON learning_chat_attempts (chat_id);

CREATE TABLE IF NOT EXISTS learning_module_progress (
        id VARCHAR(64) PRIMARY KEY,
        chat_id VARCHAR(64) NOT NULL REFERENCES learning_chats(id) ON DELETE CASCADE,
        module_id VARCHAR(64) NOT NULL,
        lesson_viewed INTEGER NOT NULL DEFAULT 0,
        best_correct INTEGER NOT NULL DEFAULT 0,
        total_questions INTEGER NOT NULL DEFAULT 0,
        completed_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (chat_id, module_id)
    );

CREATE TABLE IF NOT EXISTS learning_practice_answers (
        id VARCHAR(64) PRIMARY KEY,
        chat_id VARCHAR(64) NOT NULL REFERENCES learning_chats(id) ON DELETE CASCADE,
        module_id VARCHAR(64) NOT NULL,
        question_id VARCHAR(96) NOT NULL,
        selected_index INTEGER NOT NULL,
        is_correct INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS idx_learning_practice_chat ON learning_practice_answers (chat_id, created_at);

CREATE TABLE IF NOT EXISTS learning_project_progress (
        id VARCHAR(64) PRIMARY KEY,
        user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        project_id VARCHAR(96) NOT NULL,
        milestones_done TEXT NOT NULL DEFAULT '[]',
        submission_text TEXT,
        submission_url TEXT,
        reflection_scores TEXT,
        status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'submitted')),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (user_id, project_id)
    );

CREATE TABLE IF NOT EXISTS notifications (
        id VARCHAR(64) PRIMARY KEY,
        user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        kind TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT NOT NULL DEFAULT '',
        link TEXT,
        dedupe_key TEXT NOT NULL,
        read_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (user_id, dedupe_key)
    );

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id, created_at);

CREATE TABLE IF NOT EXISTS notification_prefs (
        user_id VARCHAR(64) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        battles INTEGER NOT NULL DEFAULT 1,
        achievements INTEGER NOT NULL DEFAULT 1,
        reminders INTEGER NOT NULL DEFAULT 1,
        projects INTEGER NOT NULL DEFAULT 1,
        quiet_start TEXT,
        quiet_end TEXT
    );

-- Default-deny (matches 0003). REVOKE only where Supabase roles exist, so plain PostgreSQL also works.
ALTER TABLE learning_chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_chat_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_module_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_practice_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_project_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_prefs ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON TABLE learning_chats FROM anon, authenticated;
    REVOKE ALL ON TABLE learning_chat_messages FROM anon, authenticated;
    REVOKE ALL ON TABLE learning_chat_attempts FROM anon, authenticated;
    REVOKE ALL ON TABLE learning_module_progress FROM anon, authenticated;
    REVOKE ALL ON TABLE learning_practice_answers FROM anon, authenticated;
    REVOKE ALL ON TABLE learning_project_progress FROM anon, authenticated;
    REVOKE ALL ON TABLE notifications FROM anon, authenticated;
    REVOKE ALL ON TABLE notification_prefs FROM anon, authenticated;
  END IF;
END $$;

COMMIT;
