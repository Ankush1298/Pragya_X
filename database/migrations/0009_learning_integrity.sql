-- Activate completed curated learning catalogs; isolate direct database clients.
UPDATE subjects SET is_active = TRUE WHERE id IN ('subj_python','subj_biology','subj_business','subj_aiml');
DO $$ DECLARE t TEXT; r TEXT; BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
    FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=r) THEN
        EXECUTE format('REVOKE ALL ON TABLE %I FROM %I',t,r);
      END IF;
    END LOOP;
  END LOOP;
END $$;
CREATE INDEX IF NOT EXISTS idx_xp_ledger_user ON xp_ledger(user_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_battles_p1 ON battles(player_one_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_battles_p2 ON battles(player_two_id,created_at DESC);
