-- Earlier learning and competition timestamps represent UTC. Preserve the instant explicitly.
DO $$ DECLARE c RECORD; BEGIN
 FOR c IN SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public' AND data_type='timestamp without time zone' LOOP
  EXECUTE format('ALTER TABLE %I ALTER COLUMN %I TYPE TIMESTAMPTZ USING %I AT TIME ZONE ''UTC''',c.table_name,c.column_name,c.column_name);
 END LOOP;
END $$;
ALTER TABLE learning_chats ADD CONSTRAINT fk_learning_chat_subject FOREIGN KEY(subject_id) REFERENCES subjects(id);
ALTER TABLE xp_ledger ADD CONSTRAINT fk_xp_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE referrals ADD CONSTRAINT fk_referrer FOREIGN KEY(referrer_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE referrals ADD CONSTRAINT fk_referee FOREIGN KEY(referee_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE battle_invitations ADD CONSTRAINT fk_invitation_sender FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE battle_invitations ADD CONSTRAINT fk_invitation_recipient FOREIGN KEY(recipient_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE challenge_submissions ADD CONSTRAINT fk_challenge_student FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE challenge_submissions ADD CONSTRAINT fk_challenge_source FOREIGN KEY(challenge_id) REFERENCES challenge_library(id);
ALTER TABLE certificates ADD CONSTRAINT fk_certificate_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX idx_team_contributions_team ON team_contributions(team_id,created_at DESC);
CREATE UNIQUE INDEX uq_learning_chat_sequence ON learning_chat_messages(chat_id,seq);
