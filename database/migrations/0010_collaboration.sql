-- Persistent teams, contribution evidence, shared work and member-only communications.
CREATE TABLE teams (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, owner_id VARCHAR(64) NOT NULL REFERENCES users(id),
 project_id TEXT NOT NULL, submission TEXT, submitted_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE team_members (
 team_id TEXT REFERENCES teams(id) ON DELETE CASCADE, user_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
 project_role TEXT NOT NULL DEFAULT 'Collaborator', joined_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(team_id,user_id)
);
CREATE TABLE team_invitations (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
 user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','declined')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(team_id,user_id)
);
CREATE TABLE team_tasks (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE, title TEXT NOT NULL,
 assignee_id VARCHAR(64) REFERENCES users(id), deadline TIMESTAMPTZ,
 status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','done')),
 created_by VARCHAR(64) NOT NULL REFERENCES users(id), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE team_messages (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
 user_id VARCHAR(64) NOT NULL REFERENCES users(id), body TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE team_contributions (
 id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
 user_id VARCHAR(64) NOT NULL REFERENCES users(id), action TEXT NOT NULL, evidence JSONB NOT NULL DEFAULT '{}',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_team_members_user ON team_members(user_id);
CREATE INDEX idx_team_tasks_team ON team_tasks(team_id);
CREATE INDEX idx_team_messages_team ON team_messages(team_id,created_at);
DO $$ DECLARE t TEXT; r TEXT; BEGIN
 FOREACH t IN ARRAY ARRAY['teams','team_members','team_invitations','team_tasks','team_messages','team_contributions'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
  FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
   IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=r) THEN EXECUTE format('REVOKE ALL ON TABLE %I FROM %I',t,r); END IF;
  END LOOP;
 END LOOP;
END $$;
