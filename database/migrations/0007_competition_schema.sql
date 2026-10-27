-- Competition schema and deterministic catalog recovered from the existing repository.
CREATE TABLE IF NOT EXISTS challenge_library (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                title TEXT NOT NULL,
                topic TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                description TEXT NOT NULL,
                code_snippet TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                explanation TEXT NOT NULL,
                points INTEGER NOT NULL DEFAULT 50,
                is_active INTEGER NOT NULL DEFAULT 1,
                scheduled_date TEXT,
                created_by TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS challenge_submissions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                challenge_id TEXT NOT NULL,
                submitted_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                points_awarded INTEGER NOT NULL DEFAULT 0,
                completed_date TEXT NOT NULL,
                submitted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, challenge_id)
            );

CREATE TABLE IF NOT EXISTS user_streaks (
                user_id TEXT PRIMARY KEY,
                current_streak INTEGER NOT NULL DEFAULT 0,
                longest_streak INTEGER NOT NULL DEFAULT 0,
                last_activity_date TEXT,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS battle_invitations (
                id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                recipient_name TEXT NOT NULL,
                subject_id TEXT NOT NULL DEFAULT 'subj_python',
                status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, ACCEPTED, REJECTED, EXPIRED, CANCELLED
                battle_id TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS battles (
                id TEXT PRIMARY KEY,
                player_one_id TEXT NOT NULL,
                player_one_name TEXT NOT NULL,
                player_two_id TEXT NOT NULL,
                player_two_name TEXT NOT NULL,
                subject_id TEXT NOT NULL DEFAULT 'subj_python',
                status TEXT NOT NULL DEFAULT 'CREATED', -- CREATED, ACTIVE, COMPLETED, CANCELLED
                questions_json TEXT NOT NULL,
                player_one_answers TEXT DEFAULT '{}',
                player_two_answers TEXT DEFAULT '{}',
                player_one_ready INTEGER NOT NULL DEFAULT 0,
                player_two_ready INTEGER NOT NULL DEFAULT 0,
                player_one_time REAL DEFAULT 0.0,
                player_two_time REAL DEFAULT 0.0,
                winner_id TEXT,
                outcome TEXT, -- WIN, TIE
                result_json TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS battle_stats (
                user_id TEXT PRIMARY KEY,
                total_battles INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                ties INTEGER NOT NULL DEFAULT 0,
                win_streak INTEGER NOT NULL DEFAULT 0,
                battle_xp INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                org_type TEXT NOT NULL, -- PLATFORM, STUDENT, COLLEGE, COMPANY
                domain TEXT,
                description TEXT NOT NULL,
                logo_url TEXT,
                is_verified INTEGER NOT NULL DEFAULT 0,
                created_by_user_id TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS hosted_competitions (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                host_type TEXT NOT NULL, -- PLATFORM, STUDENT, COLLEGE, COMPANY
                subject_id TEXT NOT NULL,
                difficulty TEXT NOT NULL DEFAULT 'Intermediate',
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                eligibility_rules TEXT NOT NULL DEFAULT 'OPEN',
                questions_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'SCHEDULED', -- DRAFT, SCHEDULED, ACTIVE, COMPLETED, ARCHIVED
                created_by_user_id TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS competition_submissions (
                id TEXT PRIMARY KEY,
                competition_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                percentage REAL NOT NULL,
                time_taken_seconds REAL NOT NULL,
                submitted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(competition_id, user_id)
            );

CREATE TABLE IF NOT EXISTS xp_ledger (
                id TEXT PRIMARY KEY,
                event_key TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                points_delta INTEGER NOT NULL,
                reason TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                origin TEXT NOT NULL DEFAULT 'live',
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS user_referral_codes (
                user_id TEXT PRIMARY KEY,
                referral_code TEXT UNIQUE NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS referrals (
                id TEXT PRIMARY KEY,
                referrer_id TEXT NOT NULL,
                referee_id TEXT UNIQUE NOT NULL,
                referral_code TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, QUALIFIED, REWARDED
                milestone_type TEXT,
                referrer_reward_points INTEGER NOT NULL DEFAULT 150,
                referee_reward_points INTEGER NOT NULL DEFAULT 50,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                qualified_at TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS certificates (
                id TEXT PRIMARY KEY,
                verification_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                cert_type TEXT NOT NULL, -- ASSESSMENT, BATTLE_WINNER, COMPETITION_WINNER, TRACK_COMPLETION
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                verification_hash TEXT NOT NULL,
                issued_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE IF NOT EXISTS reward_catalog (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                xp_cost INTEGER NOT NULL,
                icon TEXT NOT NULL DEFAULT 'gift',
                stock INTEGER NOT NULL DEFAULT 100,
                is_active INTEGER NOT NULL DEFAULT 1
            );

CREATE TABLE IF NOT EXISTS reward_redemptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                reward_id TEXT NOT NULL,
                xp_spent INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'CONFIRMED',
                redeemed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
INSERT INTO challenge_library (
                    id, subject_id, title, topic, difficulty, description, code_snippet,
                    option_a, option_b, option_c, option_d, correct_option, explanation,
                    points, is_active, scheduled_date, created_by
                )
                VALUES ('chal_py_01', 'subj_python', 'List Mutation & References', 'Data Structures', 'Medium', 'Determine matrix output when shallow multiplying inner lists.', 'matrix = [[0] * 3] * 3
matrix[0][0] = 7
print([row[0] for row in matrix])', '[7, 0, 0]', '[7, 7, 7]', '[[7, 0, 0], [0, 0, 0], [0, 0, 0]]', 'TypeError', 'B', 'Multiplying a list duplicates references to the identical list object in memory.', 50, 1, NULL, 'system') ON CONFLICT DO NOTHING;
INSERT INTO challenge_library (
                    id, subject_id, title, topic, difficulty, description, code_snippet,
                    option_a, option_b, option_c, option_d, correct_option, explanation,
                    points, is_active, scheduled_date, created_by
                )
                VALUES ('chal_py_02', 'subj_python', 'Scope Resolution: LEGB Rule', 'Functions & Scope', 'Medium', 'Identify variable lookup resolution order in Python.', 'x = ''global''
def outer():
    x = ''outer''
    def inner():
        return x
    return inner()
print(outer())', 'global', 'outer', 'None', 'UnboundLocalError', 'B', 'Python checks enclosing local scopes before module global scope.', 50, 1, NULL, 'system') ON CONFLICT DO NOTHING;
INSERT INTO challenge_library (
                    id, subject_id, title, topic, difficulty, description, code_snippet,
                    option_a, option_b, option_c, option_d, correct_option, explanation,
                    points, is_active, scheduled_date, created_by
                )
                VALUES ('chal_py_03', 'subj_python', 'Tuple Immutability & Dict Keys', 'Collections & Hashing', 'Easy', 'Understand why tuples are valid dictionary keys while lists are not.', 'valid_key = (1, 2)
invalid_key = [1, 2]
d = {valid_key: ''ok''}
print(d[valid_key])', 'TypeError', 'ok', 'None', '{ (1, 2): ''ok'' }', 'B', 'Tuples with immutable elements are hashable and thus valid dictionary keys.', 50, 1, NULL, 'system') ON CONFLICT DO NOTHING;
INSERT INTO challenge_library (
                    id, subject_id, title, topic, difficulty, description, code_snippet,
                    option_a, option_b, option_c, option_d, correct_option, explanation,
                    points, is_active, scheduled_date, created_by
                )
                VALUES ('chal_py_04', 'subj_python', 'List Comprehension vs Generator', 'Generators & Memory', 'Hard', 'Distinguish eager memory allocation from lazy iterator generation.', 'import sys
gen = (x for x in range(10000))
lst = [x for x in range(10000)]
print(sys.getsizeof(gen) < sys.getsizeof(lst))', 'True', 'False', 'TypeError', 'ZeroDivisionError', 'A', 'Generators produce items on demand with O(1) memory overhead.', 75, 1, NULL, 'system') ON CONFLICT DO NOTHING;
INSERT INTO challenge_library (
                    id, subject_id, title, topic, difficulty, description, code_snippet,
                    option_a, option_b, option_c, option_d, correct_option, explanation,
                    points, is_active, scheduled_date, created_by
                )
                VALUES ('chal_py_05', 'subj_python', 'Dictionary Comprehensions', 'Functional Python', 'Medium', 'Calculate dictionary comprehension mapping.', 'd = {k: k**2 for k in range(4) if k % 2 == 1}
print(sum(d.values()))', '10', '16', '9', '8', 'A', 'k=1 -> 1, k=3 -> 9. 1 + 9 = 10.', 50, 1, NULL, 'system') ON CONFLICT DO NOTHING;
INSERT INTO organizations (id, name, org_type, domain, description, is_verified, created_by_user_id)
                VALUES ('org_pragyax', 'PragyaX Platform', 'PLATFORM', 'pragyax.org', 'Official PragyaX platform challenges', 1, 'system_admin') ON CONFLICT DO NOTHING;
INSERT INTO organizations (id, name, org_type, domain, description, is_verified, created_by_user_id)
                VALUES ('org_iitd', 'Demo College Club (sample data)', 'COLLEGE', 'college.example', 'DEMO organisation for walkthroughs; not a real institution', 1, 'system_admin') ON CONFLICT DO NOTHING;
INSERT INTO organizations (id, name, org_type, domain, description, is_verified, created_by_user_id)
                VALUES ('org_google', 'Demo Company (sample data)', 'COMPANY', 'company.example', 'DEMO organisation for walkthroughs; not a real company', 1, 'system_admin') ON CONFLICT DO NOTHING;
INSERT INTO reward_catalog (id, title, description, category, xp_cost, icon, stock, is_active)
                VALUES ('rwd_swag_sticker', 'PragyaX Hacker Hologram Sticker Pack', 'Exclusive holographic physical stickers', 'SWAG', 200, 'sparkles', 500, 1) ON CONFLICT DO NOTHING;
INSERT INTO reward_catalog (id, title, description, category, xp_cost, icon, stock, is_active)
                VALUES ('rwd_pro_badge', 'Python Virtuoso Profile Badge', 'Permanent golden badge on leaderboards', 'DIGITAL', 350, 'award', 999, 1) ON CONFLICT DO NOTHING;
INSERT INTO reward_catalog (id, title, description, category, xp_cost, icon, stock, is_active)
                VALUES ('rwd_mentor_session', '1-on-1 AI & Systems Engineering Mentorship', '30-minute career & code review session', 'MENTORSHIP', 1000, 'user-check', 20, 1) ON CONFLICT DO NOTHING;
INSERT INTO reward_catalog (id, title, description, category, xp_cost, icon, stock, is_active)
                VALUES ('rwd_cert_voucher', 'Verified Course Completion Certificate Voucher', 'Free tamper-evident certificate issuance', 'CERTIFICATE', 500, 'file-text', 999, 1) ON CONFLICT DO NOTHING;

DO $$ DECLARE t TEXT; BEGIN FOREACH t IN ARRAY ARRAY['challenge_library','challenge_submissions','user_streaks','battle_invitations','battles','battle_stats','organizations','hosted_competitions','competition_submissions','xp_ledger','user_referral_codes','referrals','certificates','reward_catalog','reward_redemptions'] LOOP EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t); END LOOP; END $$;
