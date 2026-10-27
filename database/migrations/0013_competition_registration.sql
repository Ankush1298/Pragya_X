CREATE TABLE competition_registrations (
 comp_id TEXT NOT NULL REFERENCES hosted_competitions(id) ON DELETE CASCADE,
 user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 registered_at TIMESTAMPTZ NOT NULL DEFAULT now(), started_at TIMESTAMPTZ,
 PRIMARY KEY(comp_id,user_id)
);
CREATE INDEX idx_competition_registration_user ON competition_registrations(user_id);
ALTER TABLE competition_registrations ENABLE ROW LEVEL SECURITY;
DO $$ DECLARE r TEXT; BEGIN FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r) THEN EXECUTE format('REVOKE ALL ON competition_registrations FROM %I',r); END IF;
END LOOP; END $$;
