> Historical design/test record. Database and release claims here are superseded by POSTGRESQL_ONLY_VERIFICATION.md and FINAL_PRODUCT_AUDIT.md (27 October 2026).

# Architecture & team boundaries

```
React (Vite, :5173) ──/api proxy──▶ FastAPI (:8000) ──▶ Repository ──▶ SQLite (pragyax.db)
                                         │                                 (Supabase later)
                                         └──▶ ai.factory.get_ai_provider() ──▶ MockAIProvider
                                                                              (RealAIProvider later)
```

Request flow: router (validation, auth via `get_current_user` dependency) → `Repository` (all SQL)
and/or AI provider → Pydantic response schema. Routers never contain SQL; the AI layer never touches the DB.

## Module ownership & extension points

| Owner | Area | Files | How to extend without breaking the MVP |
|---|---|---|---|
| **Ankush** | Architecture, integration, challenges (+ future competitions, referrals, certificates) | `backend/app/routers/challenges.py`, `docs/`, challenge methods in `repository.py` | Add new routers under `routers/` and mount them in `main.py`; keep each feature in its own router + schema file |
| **Arsh** | FastAPI backend | `backend/app/` (routers, schemas, services, config) | Keep response schemas stable (frontend types mirror them in `frontend/src/api/types.ts`) |
| **Ekansh** | AI/ML evaluation | `ai/` | Implement `generate_chat_response` / `evaluate_assessment` in `ai/real_provider.py` (contract in `ai/base.py`), then flip its `is_mock`. Select with `AI_PROVIDER`. Mock stays the default |
| **Nagin** | Supabase PostgreSQL | `database/`, `backend/app/database/` | Implement the same `Repository` method signatures against Postgres; `database/schema.sql` mirrors the SQLite tables |
| **Shoeb** | React frontend | `frontend/src/` | Pages are independent; all HTTP goes through `src/api/client.ts`; styles are tokens in `src/styles.css` |

## Security model (demo)
- Passwords: PBKDF2-HMAC-SHA256, 100k iterations, per-user random salt, constant-time compare.
- Sessions: random 32-byte bearer tokens in `active_sessions`, expire after `ACCESS_TOKEN_EXPIRE_MINUTES`, deleted on logout.
- Isolation: every user-scoped query filters by the authenticated `user_id` (attempts, chat, dashboard, challenges).
- Assessment integrity: questions endpoint never returns `correct_option`/`explanation`; grading uses the DB key only.

## Known limitations
- Demo auth only: tokens in `localStorage`, no rate limiting, password reset, email verification or CSRF hardening.
- Mock AI is a keyword → lesson lookup (~19 core Python topics); it cannot answer arbitrary questions.
- One fixed 5-question set; no question bank, randomisation or time limit. Retakes allowed and all saved.
- One static daily challenge (no rotation by date).
- SQLite with a connection per request: fine for a demo, not for concurrent production load.
- Supabase is documented, not connected.

## Not implemented (future modules, intentionally not started)
1v1 battles & real-time matchmaking · company challenges · referral system · certificate generation/verification ·
leaderboards · more subjects (currently "Coming Soon" cards).

## Next integration tasks
1. **Ekansh:** real LLM calls in `ai/real_provider.py` with mock fallback on error/timeout.
2. **Nagin:** `SupabaseRepository` + select by env var; run `database/schema.sql` + `seed.sql` in Supabase; RLS policies.
3. **Arsh:** move to Supabase Auth or JWT; rate-limit auth routes; Alembic-style migrations.
4. **Shoeb:** question bank UI, accessibility pass with a screen reader, theme toggle.
5. **Ankush:** rotating daily challenges, leaderboard, then battles/certificates.
