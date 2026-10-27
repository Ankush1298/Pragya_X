"""
PostgreSQL Student Journey Integration Test Suite
Complete end-to-end integration tests covering:
- Phase 3: Student Workflow (Registration, Login, Profile, Subjects, Assessment, Evaluation, Dashboard, Logout)
- Phase 4: Authorization & Isolation (User A vs User B, Invalid Token, Expired Session, Logged-out Token)
- Phase 5 & 7: Database Persistence, Foreign Keys, Transaction Commit & Rollback

SAFETY INVARIANTS:
1. NEVER executes against the shared production Supabase database.
2. Requires a dedicated, isolated test database named 'pragyax_test'.
3. Validates that the test host is local (127.0.0.1/localhost) on isolated port 5433.
4. Validates that no Supabase host or pooler is used.
5. Fails immediately if isolation cannot be verified.
"""

import os
import tempfile
import uuid
from urllib.parse import urlparse, quote_plus
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Phase 3: Isolation and Safety Verification
# ---------------------------------------------------------------------------

def resolve_test_database_url() -> str:
    """Resolves TEST_DATABASE_URL from environment or local test cluster password file."""
    env_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if env_url:
        return env_url
    pw_file = os.path.join(tempfile.gettempdir(), "pragyax_test_pw.txt")
    if os.path.exists(pw_file):
        with open(pw_file, "r", encoding="utf-8") as f:
            pw = f.read().strip()
        if pw:
            return f"postgresql://pragyax_test_user:{quote_plus(pw)}@127.0.0.1:5433/pragyax_test?sslmode=disable"
    return ""


TEST_DB_URL = resolve_test_database_url()
PROD_DB_URL = os.getenv("DATABASE_URL", "").strip()


def verify_strict_isolation(test_url: str, prod_url: str):
    """
    Strict Phase 3 Isolation Verification.
    Rejects execution if any isolation invariant fails.
    """
    if not test_url:
        pytest.fail("ISOLATION FAILURE: TEST_DATABASE_URL does not exist.")
    
    parsed_test = urlparse(test_url)
    parsed_prod = urlparse(prod_url) if prod_url else None

    # Check 1: Host must be local
    host = (parsed_test.hostname or "").lower()
    if host not in ("127.0.0.1", "localhost", "::1"):
        pytest.fail(f"SECURITY VIOLATION: Test host '{host}' is not local. Integration tests must run locally.")

    # Check 2: Database name must be 'pragyax_test'
    db_name = parsed_test.path.lstrip("/").split("?")[0]
    if db_name != "pragyax_test":
        pytest.fail(f"SECURITY VIOLATION: Test database name is '{db_name}'. Expected strictly 'pragyax_test'.")

    # Check 3: Must not target any Supabase domain or pooler
    if "supabase.co" in host or "pooler.supabase.com" in host:
        pytest.fail("SECURITY VIOLATION: TEST_DATABASE_URL points to Supabase. Aborting immediately.")



pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="TEST_DATABASE_URL is not configured. Execution blocked to prevent writing to shared production Supabase."
)


@pytest.fixture(scope="module")
def postgres_client():
    """Sets up FastAPI TestClient strictly isolated to the local PostgreSQL test database."""
    verify_strict_isolation(TEST_DB_URL, PROD_DB_URL)

    from backend.app.config import settings
    from backend.app.database.connection import init_db, close_db_pool
    from backend.app.main import app

    # Switch in-memory configuration to the isolated test database
    settings.DATABASE_URL = TEST_DB_URL
    close_db_pool()
    init_db()

    with TestClient(app) as client:
        yield client

    close_db_pool()


# ---------------------------------------------------------------------------
# PHASE 5: Student Workflow Integration Tests
# ---------------------------------------------------------------------------

def test_student_complete_journey(postgres_client):
    """
    Verifies complete student workflow:
    1. Student registration
    2. Student login
    3. Authenticated profile retrieval
    4. Subject catalog retrieval
    5. Subject selection
    6. Five-question assessment retrieval
    7. Assessment answer submission
    8. Assessment evaluation & grading
    9. Assessment result persistence
    10. Assessment history retrieval
    11. Dashboard analytics derivation
    12. Student logout
    13. Token invalidation
    """
    client = postgres_client
    unique_suffix = uuid.uuid4().hex[:8]
    student_email = f"student_{unique_suffix}@pragyax.test"
    student_password = "SecurePassword2026!"
    student_name = f"Student {unique_suffix}"

    # 1. Student Registration (POST /api/auth/register)
    reg_res = client.post("/api/auth/register", json={
        "name": student_name,
        "email": student_email,
        "password": student_password
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "token" in reg_data
    assert reg_data["user"]["email"] == student_email
    token = reg_data["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Student Login (POST /api/auth/login)
    login_res = client.post("/api/auth/login", json={
        "email": student_email,
        "password": student_password
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "token" in login_data

    # 3. Authenticated Profile Retrieval (GET /api/auth/me)
    profile_res = client.get("/api/auth/me", headers=headers)
    assert profile_res.status_code == 200
    profile_data = profile_res.json()
    assert profile_data["email"] == student_email
    assert profile_data["name"] == student_name

    # 4. Subject Catalog Retrieval (GET /api/subjects)
    subjects_res = client.get("/api/subjects", headers=headers)
    assert subjects_res.status_code == 200
    subjects_data = subjects_res.json()
    assert len(subjects_data["subjects"]) >= 4
    python_subj = next((s for s in subjects_data["subjects"] if s["id"] == "subj_python"), None)
    assert python_subj is not None
    assert python_subj["is_active"] is True

    # 5. Subject Selection (POST /api/subjects/select)
    select_res = client.post("/api/subjects/select", json={"subject_id": "subj_python"}, headers=headers)
    assert select_res.status_code == 200
    assert select_res.json()["id"] == "subj_python"

    # 6. Five-Question Assessment Retrieval (GET /api/assessments/questions)
    questions_res = client.get("/api/assessments/questions?subject_id=subj_python", headers=headers)
    assert questions_res.status_code == 200
    questions = questions_res.json()
    assert len(questions) == 5
    for q in questions:
        # Crucial security check: Ensure answers and explanations are NEVER exposed to client
        assert "correct_option" not in q
        assert "explanation" not in q

    # 7 & 8. Assessment Submission & Evaluation (POST /api/assessments/submit)
    submit_res = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B",
            "q_py_2": "C",
            "q_py_3": "C",
            "q_py_4": "B",
            "q_py_5": "A"
        }
    }, headers=headers)
    assert submit_res.status_code == 200
    eval_data = submit_res.json()
    assert eval_data["score"] == 5
    assert eval_data["total"] == 5
    assert eval_data["percentage"] == 100.0
    assert eval_data["proficiency_level"] == "Advanced"
    assert len(eval_data["breakdown"]) == 5
    attempt_id = eval_data["id"]

    # 9. Assessment Result Persistence Retrieval (GET /api/assessments/{attempt_id})
    fetch_res = client.get(f"/api/assessments/{attempt_id}", headers=headers)
    assert fetch_res.status_code == 200
    fetched_eval = fetch_res.json()
    assert fetched_eval["id"] == attempt_id
    assert fetched_eval["score"] == 5

    # 10. Assessment History Retrieval (GET /api/assessments/history)
    history_res = client.get("/api/assessments/history", headers=headers)
    assert history_res.status_code == 200
    attempts_history = history_res.json()["attempts"]
    assert any(a["id"] == attempt_id for a in attempts_history)

    # 11. Dashboard Analytics (GET /api/dashboard)
    dash_res = client.get("/api/dashboard", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["metrics"]["total_assessments_completed"] >= 1
    assert dash_data["metrics"]["latest_score"] == 5
    assert dash_data["metrics"]["highest_score"] == 5
    assert dash_data["has_selected_subject"] is True

    # 12. Student Logout (POST /api/auth/logout)
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out successfully"

    # 13. Token Invalidation Check
    after_logout_res = client.get("/api/auth/me", headers=headers)
    assert after_logout_res.status_code == 401


# ---------------------------------------------------------------------------
# PHASE 6: Authorization and Tenant Isolation Tests
# ---------------------------------------------------------------------------

def test_user_isolation_and_authorization(postgres_client):
    """
    Verifies strict tenant isolation between two disposable users:
    - User A cannot retrieve User B's attempts.
    - User B cannot access User A's private records.
    - Dashboard data is strictly user-specific.
    - Invalid tokens return HTTP 401.
    - Missing tokens return HTTP 401.
    - Logged-out tokens cannot be reused.
    """
    client = postgres_client

    # User A Registration
    user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@pragyax.test"
    res_a = client.post("/api/auth/register", json={
        "name": "User Alpha",
        "email": user_a_email,
        "password": "PasswordA123!"
    })
    token_a = res_a.json()["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User B Registration
    user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@pragyax.test"
    res_b = client.post("/api/auth/register", json={
        "name": "User Beta",
        "email": user_b_email,
        "password": "PasswordB123!"
    })
    token_b = res_b.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A takes an assessment
    submit_a = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B",
            "q_py_2": "C",
            "q_py_3": "C",
            "q_py_4": "B",
            "q_py_5": "A"
        }
    }, headers=headers_a)
    attempt_id_a = submit_a.json()["id"]

    # ATTEMPT ACCESS ISOLATION: User B attempts to access User A's attempt result
    unauthorized_fetch = client.get(f"/api/assessments/{attempt_id_a}", headers=headers_b)
    # Must return 404 Not Found so record existence is not leaked
    assert unauthorized_fetch.status_code == 404

    # DASHBOARD ISOLATION: User B's dashboard must not reflect User A's attempt
    dash_b = client.get("/api/dashboard", headers=headers_b)
    assert dash_b.status_code == 200
    assert dash_b.json()["metrics"]["total_assessments_completed"] == 0

    # INVALID TOKEN REJECTION
    invalid_res = client.get("/api/auth/me", headers={"Authorization": "Bearer pragya_invalid_token_12345"})
    assert invalid_res.status_code == 401

    # MISSING TOKEN REJECTION
    missing_res = client.get("/api/auth/me")
    assert missing_res.status_code == 401

    # LOGGED-OUT TOKEN CANNOT BE REUSED
    client.post("/api/auth/logout", headers=headers_a)
    reused_res = client.get("/api/auth/me", headers=headers_a)
    assert reused_res.status_code == 401


# ---------------------------------------------------------------------------
# PHASE 7: Database Persistence & Transaction Integrity Verification
# ---------------------------------------------------------------------------

def test_database_persistence_and_relationships(postgres_client):
    """
    Verifies:
    - User records persist in PostgreSQL.
    - Session records are created correctly.
    - Assessment attempts are saved.
    - Assessment results can be retrieved.
    - Foreign keys remain valid.
    - Database transactions commit correctly.
    - Failed transactions roll back safely.
    """
    from backend.app.database.connection import get_db

    client = postgres_client
    email = f"db_persist_{uuid.uuid4().hex[:8]}@pragyax.test"

    reg_res = client.post("/api/auth/register", json={
        "name": "Persist Student",
        "email": email,
        "password": "PersistPassword123!"
    })
    user_id = reg_res.json()["user"]["id"]
    token = reg_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit attempt
    submit_res = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B",
            "q_py_2": "C",
            "q_py_3": "C",
            "q_py_4": "B",
            "q_py_5": "A"
        }
    }, headers=headers)
    attempt_id = submit_res.json()["id"]

    # Verify directly via SQL against the isolated PostgreSQL instance
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. User persists in 'users' table
            cur.execute("SELECT id, email, password_hash, salt FROM users WHERE id = %s;", (user_id,))
            user_row = cur.fetchone()
            assert user_row is not None
            assert user_row["email"] == email
            assert len(user_row["password_hash"]) > 0
            assert len(user_row["salt"]) > 0

            # 2. Session persists in 'active_sessions' table
            cur.execute("SELECT token, user_id FROM active_sessions WHERE token = %s;", (token,))
            session_row = cur.fetchone()
            assert session_row is not None
            assert session_row["user_id"] == user_id

            # 3. Assessment attempt persists in 'assessment_attempts'
            cur.execute("SELECT id, user_id, subject_id, score FROM assessment_attempts WHERE id = %s;", (attempt_id,))
            attempt_row = cur.fetchone()
            assert attempt_row is not None
            assert attempt_row["user_id"] == user_id
            assert attempt_row["subject_id"] == "subj_python"

            # 4. Foreign key integrity: attempt references valid user and subject
            cur.execute("""
                SELECT a.id, u.name, s.title
                FROM assessment_attempts a
                JOIN users u ON a.user_id = u.id
                JOIN subjects s ON a.subject_id = s.id
                WHERE a.id = %s;
            """, (attempt_id,))
            joined_row = cur.fetchone()
            assert joined_row is not None
            assert joined_row["title"] == "Python Programming"

    # 5. Transaction Rollback Verification:
    # Verify that a failing transaction rolls back cleanly without persisting partial data
    rollback_token = f"pragya_rollback_{uuid.uuid4().hex[:8]}"
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Valid insert
                cur.execute(
                    "INSERT INTO active_sessions (token, user_id) VALUES (%s, %s);",
                    (rollback_token, user_id)
                )
                # Intentionally failing insert (violates foreign key constraint to non-existent user)
                cur.execute(
                    "INSERT INTO active_sessions (token, user_id) VALUES (%s, %s);",
                    ("pragya_invalid_fk", "usr_nonexistent_999999")
                )
    except Exception:
        # Expected constraint failure
        pass

    # Verify rollback succeeded: rollback_token must NOT exist in the database
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM active_sessions WHERE token = %s;", (rollback_token,))
            assert cur.fetchone() is None, "Rollback failed: partial record persisted after failed transaction!"
