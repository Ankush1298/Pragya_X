"""Curriculum integrity verified on the PostgreSQL migration catalog."""
import pytest
import psycopg
from backend.app.database.connection import get_db, init_db
from backend.app.database.repository import Repository
from fastapi.testclient import TestClient
from backend.app.main import app
EXPECTED_SUBJECT_IDS = [
    "subj_python",
    "subj_webdev",
    "subj_datasci",
    "subj_cloud",
    "subj_biology",
    "subj_business",
    "subj_aiml",
]

EXPECTED_ANSWER_KEYS = {
    # Python
    "q_py_1": "B",
    "q_py_2": "C",
    "q_py_3": "C",
    "q_py_4": "B",
    "q_py_5": "A",
    # Biology
    "q_bio_1": "C",
    "q_bio_2": "B",
    "q_bio_3": "B",
    "q_bio_4": "C",
    "q_bio_5": "B",
    # Business
    "q_bus_1": "C",
    "q_bus_2": "B",
    "q_bus_3": "A",
    "q_bus_4": "B",
    "q_bus_5": "B",
    # AI/ML
    "q_aiml_1": "B",
    "q_aiml_2": "B",
    "q_aiml_3": "B",
    "q_aiml_4": "B",
    "q_aiml_5": "B",
}

def test_fresh_postgres_seven_subjects():
    """1. Fresh PostgreSQL database has 7 subjects."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, slug, title, is_active FROM subjects ORDER BY id;")
        rows = cursor.fetchall()
        assert len(rows) == 7
        subject_ids = [r["id"] for r in rows]
        for sid in EXPECTED_SUBJECT_IDS:
            assert sid in subject_ids

def test_twenty_assessment_questions_exist():
    """2. Exactly 20 assessment questions exist."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM assessment_questions;")
        row = cursor.fetchone()
        assert row["total"] == 20

def test_four_tracks_have_five_mcqs_each():
    """3. Each of four assessment tracks has exactly 5 MCQs sequenced 1..5."""
    tracks = ["subj_python", "subj_biology", "subj_business", "subj_aiml"]
    with get_db() as conn:
        cursor = conn.cursor()
        for track_id in tracks:
            cursor.execute(
                """
                SELECT question_number, id, correct_option
                FROM assessment_questions
                WHERE subject_id = ?
                ORDER BY question_number ASC;
            """,
                (track_id,),
            )
            questions = cursor.fetchall()
            assert len(questions) == 5, (
                f"Track {track_id} does not have exactly 5 questions"
            )
            numbers = [q["question_number"] for q in questions]
            assert numbers == [1, 2, 3, 4, 5], (
                f"Track {track_id} has broken slot sequencing"
            )

def test_subject_ids_match_postgres_migration():
    """4. Subject IDs match PostgreSQL migration 0004."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM subjects;")
        db_subject_ids = {r["id"] for r in cursor.fetchall()}
        assert db_subject_ids == set(EXPECTED_SUBJECT_IDS)

def test_question_ids_match_postgres_migration():
    """5. Question IDs match PostgreSQL migration 0004."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assessment_questions;")
        db_question_ids = {r["id"] for r in cursor.fetchall()}
        assert db_question_ids == set(EXPECTED_ANSWER_KEYS.keys())

def test_correct_answers_match_postgres_reference():
    """6. Correct answers match PostgreSQL reference keys."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, correct_option FROM assessment_questions;")
        for row in cursor.fetchall():
            qid = row["id"]
            expected_opt = EXPECTED_ANSWER_KEYS[qid]
            assert row["correct_option"] == expected_opt, (
                f"Answer mismatch for {qid}: expected {expected_opt}, got {row['correct_option']}"
            )

def test_repeated_initialization_is_idempotent():
    """9. Repeated initialization does not create duplicate records."""
    # Call init_db() multiple times
    init_db()
    init_db()
    init_db()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM subjects;")
        assert cursor.fetchone()["total"] == 7
        cursor.execute("SELECT COUNT(*) AS total FROM assessment_questions;")
        assert cursor.fetchone()["total"] == 20
        cursor.execute("SELECT COUNT(*) AS total FROM daily_challenges;")
        assert cursor.fetchone()["total"] == 1

def test_existing_student_records_preserved():
    """10. Existing student records remain intact after re-initialization."""
    user = Repository.create_user(
        "Test Student", "student@pragyax.test", "dummy_hash_123", "dummy_salt_123"
    )
    user_id = user["id"]

    # Re-run initialization
    init_db()

    # User and preferences must still exist
    fetched = Repository.get_user_by_id(user_id)
    assert fetched is not None
    assert fetched["email"] == "student@pragyax.test"

    pref = Repository.get_user_selected_subject(user_id)
    assert pref is not None
    assert pref["id"] == "subj_python"

def test_existing_backend_api_functional():
    """13. Existing backend API endpoints remain functional with fresh PostgreSQL schema."""
    with TestClient(app) as client:
        # Health check
        h_res = client.get("/api/health")
        assert h_res.status_code == 200
        assert "PostgreSQL" in h_res.json()["database"]

        # Subjects list has 7 subjects
        reg_res = client.post(
            "/api/auth/register",
            json={
                "name": "Integration Student",
                "email": "intstudent@pragyax.test",
                "password": "validPassword123!",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        subj_res = client.get("/api/subjects", headers=headers)
        assert subj_res.status_code == 200
        subjects = subj_res.json()["subjects"]
        assert len(subjects) == 7

        # Completed curated subjects can be selected
        sel_res = client.post(
            "/api/subjects/select", json={"subject_id": "subj_biology"}, headers=headers
        )
        assert sel_res.status_code == 200
        assert sel_res.json()["id"] == "subj_biology"

        # Questions for Python loads exactly 5 MCQs
        q_res = client.get(
            "/api/assessments/questions?subject_id=subj_python", headers=headers
        )
        assert q_res.status_code == 200
        questions = q_res.json()
        assert len(questions) == 5


def test_active_curated_subjects():
    with get_db() as conn:
        cur=conn.cursor();cur.execute("SELECT id FROM subjects WHERE is_active")
        assert {r['id'] for r in cur.fetchall()} == {'subj_python','subj_biology','subj_business','subj_aiml'}


def test_postgres_constraint_rollback():
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with get_db() as conn:
            conn.cursor().execute("INSERT INTO active_sessions(token,user_id) VALUES ('invalid','missing')")
    with get_db() as conn:
        cur=conn.cursor();cur.execute("SELECT * FROM active_sessions WHERE token='invalid'")
        assert cur.fetchone() is None


def test_indexes_exist():
    with get_db() as conn:
        cur=conn.cursor();cur.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public'")
        indexes={r['indexname'] for r in cur.fetchall()}
        assert 'idx_xp_ledger_user' in indexes
        assert 'idx_learning_chats_user' in indexes
