-- ============================================================================
-- PragyaX PostgreSQL Database Migration
-- Version: 0005
-- Description: Learner roadmap progress tracking table with RLS lockdown.
-- Author: Nagin (Senior Database Architect & Supabase Specialist)
-- Target: PostgreSQL 14+ / Supabase PostgreSQL
-- 
-- ARCHITECTURAL RATIONALE:
-- 1. SEPARATION OF CONCERNS: Roadmap curricula and prerequisite DAGs are generated
--    deterministically in memory by backend/app/services/roadmap_service.py.
--    This table stores ONLY mutable student progression state (module completion).
-- 2. CONTRACT COMPATIBILITY: Uses VARCHAR(64) for user_id and subject_id, and
--    VARCHAR(128) for stable module identifiers (e.g. 'mod_py_types').
-- 3. STRICT COMPLETION CONSISTENCY: Enforces that completed modules require a
--    valid completed_at timestamp, while incomplete/reset modules MUST have
--    completed_at IS NULL. Inconsistent intermediate states are rejected.
-- 4. DEFENSIVE PREFLIGHT & RE-RUN SAFETY: Preflight checks verify prerequisite
--    tables (users, subjects) and validate column structure if the table already
--    exists, preventing silent no-ops on incompatible preexisting tables.
-- 5. LEAST-PRIVILEGE SECURITY: Completely revokes public PostgREST API access
--    (anon, authenticated) and enables Row-Level Security (RLS Default-Deny).
--    FastAPI backend access should use a reviewed application role with explicit
--    grants rather than relying on blanket superuser or BYPASSRLS privileges.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Prerequisite Catalog and Schema Compatibility Check
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    missing_cols text;
BEGIN
    -- Prerequisite 1: Core tables from 0001_initial_schema.sql must exist
    IF to_regclass('public.users') IS NULL OR to_regclass('public.subjects') IS NULL THEN
        RAISE EXCEPTION 'Prerequisite violation: users or subjects table does not exist. Please apply 0001_initial_schema.sql first.';
    END IF;

    -- Prerequisite 2: If table already exists, verify structural compatibility
    -- (Defends against silent failure of CREATE TABLE IF NOT EXISTS on divergent schemas)
    IF to_regclass('public.user_roadmap_progress') IS NOT NULL THEN
        SELECT string_agg(col, ', ') INTO missing_cols
        FROM unnest(ARRAY['user_id', 'subject_id', 'module_id', 'is_completed', 'completed_at', 'created_at', 'updated_at']) AS col
        WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'user_roadmap_progress' 
              AND column_name = col
        );

        IF missing_cols IS NOT NULL THEN
            RAISE EXCEPTION 'Schema conflict: public.user_roadmap_progress exists but is missing required column(s): %', missing_cols;
        END IF;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 2. Table: user_roadmap_progress
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_roadmap_progress (
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_id VARCHAR(64) NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    module_id VARCHAR(128) NOT NULL,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_user_roadmap_progress PRIMARY KEY (user_id, subject_id, module_id),
    CONSTRAINT chk_user_roadmap_progress_completion CHECK (
        (is_completed = TRUE AND completed_at IS NOT NULL) OR 
        (is_completed = FALSE AND completed_at IS NULL)
    )
);

-- Ensure constraint is synchronized if table pre-existed under an earlier draft
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_user_roadmap_progress_completion' 
          AND conrelid = 'public.user_roadmap_progress'::regclass
    ) THEN
        -- Drop old constraint if it does not enforce completed_at IS NULL for incomplete records
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE c.conname = 'chk_user_roadmap_progress_completion'
              AND t.relname = 'user_roadmap_progress'
              AND pg_get_constraintdef(c.oid) LIKE '%is_completed = false AND completed_at IS NULL%'
        ) THEN
            ALTER TABLE public.user_roadmap_progress 
                DROP CONSTRAINT chk_user_roadmap_progress_completion;
            ALTER TABLE public.user_roadmap_progress 
                ADD CONSTRAINT chk_user_roadmap_progress_completion CHECK (
                    (is_completed = TRUE AND completed_at IS NOT NULL) OR 
                    (is_completed = FALSE AND completed_at IS NULL)
                );
        END IF;
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 3. Query-Driven Performance Indexes
-- ----------------------------------------------------------------------------

-- Fast retrieval of completed modules for lock status calculation:
-- Used by: roadmap_service.py update_module_lock_statuses
-- Query pattern: SELECT module_id FROM user_roadmap_progress WHERE user_id = ? AND subject_id = ? AND is_completed = TRUE
CREATE INDEX IF NOT EXISTS idx_user_roadmap_progress_completed 
    ON user_roadmap_progress (user_id, subject_id) 
    WHERE is_completed = TRUE;

-- Fast index for foreign key cascade checks on subject deletions:
CREATE INDEX IF NOT EXISTS idx_user_roadmap_progress_subject 
    ON user_roadmap_progress (subject_id);

-- ----------------------------------------------------------------------------
-- 4. PostgREST Lockdown (Revoke Public Grants)
-- ----------------------------------------------------------------------------
-- PragyaX routes all learner roadmap requests through FastAPI (/api/roadmap/*).
-- Direct HTTP access via Supabase anon / authenticated roles must be blocked.
DO $$ DECLARE r TEXT; BEGIN FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=r) THEN EXECUTE format('REVOKE ALL ON TABLE user_roadmap_progress FROM %I',r); END IF; END LOOP; END $$;

-- ----------------------------------------------------------------------------
-- 5. Defense-In-Depth Row-Level Security (RLS Default-Deny)
-- ----------------------------------------------------------------------------
-- Enabling RLS without permissive public policies enforces an automatic
-- Default-Deny for unprivileged client roles accessing via PostgREST.
ALTER TABLE user_roadmap_progress ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- 6. Backend Service Least-Privilege Strategy
-- ----------------------------------------------------------------------------
-- NOTE ON BACKEND ROLE ACCESS:
-- 1. PragyaX FastAPI backend authenticates users via internal session bearer
--    tokens (e.g. usr_<hex12>), NOT Supabase Auth JWTs. auth.uid() is not used.
-- 2. Rather than granting the backend service database connection blanket
--    superuser or BYPASSRLS permissions, production environments should connect
--    via a dedicated application role (e.g., pragyax_backend_app) granted:
--      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE user_roadmap_progress TO pragyax_backend_app;
-- 3. If RLS is enforced against the application role, attach a service policy:
--      CREATE POLICY pragyax_backend_service_policy ON user_roadmap_progress
--          FOR ALL TO pragyax_backend_app USING (true) WITH CHECK (true);
-- 4. Authorization and user isolation (ensuring user_id == current_user.id)
--    must be verified at the FastAPI router/service layer.
-- ----------------------------------------------------------------------------

COMMIT;
