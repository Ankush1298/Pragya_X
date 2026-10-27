# PragyaX — AI-Powered Gamified Learning: From Theory to Practice

Hackathon prototype. A learner registers, studies with a learning chat, picks a subject, takes a
5-question assessment, gets an evaluated result that is saved, and sees real progress on a dashboard.

**Runs fully native on PostgreSQL:** Private local PostgreSQL cluster + a deterministic **Mock AI**. Zero external internet dependencies required.

```
Registration → Learning Chat → Subject Selection → 5-Question Assessment → Mock Evaluation → Saved Results → Dashboard
```
Extra features: Synchronous 1v1 Battles, Hosted Competitions, Multi-Milestone Projects, Dual-Gated Referrals, and Cryptographic Certificates.

---

## Quick start (macOS / Linux)

Requirements: Python 3.11+ (tested with 3.14), Node 18+ (tested with 26), PostgreSQL 14+.

### 1. Database Provisioning
```bash
python3 tools/local_postgres.py                 # Initializes & starts private PostgreSQL on 127.0.0.1:55433
python3 -m backend.app.database.migrate          # Applies all 13 migrations
```

### 2. Backend (Terminal 1)
```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8011
```
- API: http://127.0.0.1:8011
- Swagger docs: http://127.0.0.1:8011/docs
- Health check: http://127.0.0.1:8011/api/health

### 3. Frontend (Terminal 2)
```bash
cd frontend
VITE_BACKEND_URL=http://127.0.0.1:8011 npm run dev
```
- Web Application: http://127.0.0.1:5174 (Vite proxies `/api` to port 8011)

---

## Tests & Verification

```bash
.venv/bin/python tools/test_backend.py          # Full backend suite (714 passed, 0 failed, 6 skipped)
.venv/bin/python tools/verify_all_flows.py       # Live E2E integration test (6/6 flows verified)
cd frontend && npm run build                    # TypeScript typecheck + production build
```

---

## Documentation

- [docs/FINAL_PRODUCT_AUDIT.md](docs/FINAL_PRODUCT_AUDIT.md): Comprehensive system & test audit
- [docs/FEATURE_COMPLETION_TRACKER.md](docs/FEATURE_COMPLETION_TRACKER.md): Itemized 92-feature functional matrix
- [docs/POSTGRESQL_ONLY_VERIFICATION.md](docs/POSTGRESQL_ONLY_VERIFICATION.md): SQLite elimination proof & PostgreSQL durability
- [docs/INTEGRATION_VERIFICATION.md](docs/INTEGRATION_VERIFICATION.md): Step-by-step E2E flow execution trace
- [docs/RELEASE_READINESS.md](docs/RELEASE_READINESS.md): Judge-Demo Ready (100%) vs. Production Launch Ready
- [docs/JUDGE_DEMO_SCRIPT.md](docs/JUDGE_DEMO_SCRIPT.md): Timed 5-minute judge walkthrough
- [docs/ADOPTION_IMPACT_PLAN.md](docs/ADOPTION_IMPACT_PLAN.md): Institutional adoption & GTM strategy

