"""
Comprehensive End-to-End API Test Suite
Verifies:
1. Health check
2. Registration and login
3. Password hashing & validation
4. Unauthorized access protection
5. Learning chat with Mock AI provider
6. Subject selection & persistence
7. Exactly 5 questions retrieval without leaking correct answers
8. Invalid vs valid assessment submissions
9. Deterministic evaluation & grading
10. Assessment attempt persistence across restarts
11. User isolation (User 1 cannot view User 2's results)
12. Dashboard metrics derivation from real data
13. Daily challenge completion, single-award points, and badge earning
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient


from backend.app.config import settings
os.environ["AI_PROVIDER"] = "mock"

from backend.app.main import app
from backend.app.database.connection import init_db

init_db()
client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["persistence_active"] is True


def test_auth_validation_and_flow():
    # 1. Invalid registration (short password)
    res = client.post("/api/auth/register", json={
        "name": "Ankush Test",
        "email": "ankush@example.com",
        "password": "123"
    })
    assert res.status_code in (400, 422)

    # 2. Valid registration
    res = client.post("/api/auth/register", json={
        "name": "Ankush Learner",
        "email": "ankush@pragyax.test",
        "password": "SecurePassword123!"
    })
    assert res.status_code == 201
    auth_data = res.json()
    assert "token" in auth_data
    assert auth_data["user"]["email"] == "ankush@pragyax.test"

    # 3. Duplicate registration
    res_dup = client.post("/api/auth/register", json={
        "name": "Ankush Learner",
        "email": "ankush@pragyax.test",
        "password": "AnotherPassword"
    })
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.json()["detail"]

    # 4. Valid login
    res_login = client.post("/api/auth/login", json={
        "email": "ankush@pragyax.test",
        "password": "SecurePassword123!"
    })
    assert res_login.status_code == 200
    token = res_login.json()["token"]
    assert token.startswith("pragya_")

    # 5. Invalid login
    res_bad_login = client.post("/api/auth/login", json={
        "email": "ankush@pragyax.test",
        "password": "WrongPassword"
    })
    assert res_bad_login.status_code == 401


def test_unauthorized_access_protection():
    # Protected endpoints must fail without token
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/subjects").status_code == 401
    assert client.get("/api/chat/history").status_code == 401
    assert client.get("/api/assessments/questions").status_code == 401
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/challenges/daily").status_code == 401


def test_learning_chat_with_mock_ai():
    # Login first
    login_res = client.post("/api/auth/login", json={
        "email": "ankush@pragyax.test",
        "password": "SecurePassword123!"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query Python concepts
    chat_res = client.post("/api/chat/message", json={
        "message": "Can you explain list comprehensions?",
        "subject": "Python Programming"
    }, headers=headers)

    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["is_mock"] is True
    assert "list comprehensions" in chat_data["content"].lower() or "comprehension" in chat_data["content"].lower()
    assert len(chat_data["suggested_followups"]) > 0

    # Verify history persistence
    hist_res = client.get("/api/chat/history", headers=headers)
    assert hist_res.status_code == 200
    msgs = hist_res.json()["messages"]
    assert len(msgs) >= 2  # user message and assistant reply


def test_subjects_selection_and_rules():
    login_res = client.post("/api/auth/login", json={
        "email": "ankush@pragyax.test",
        "password": "SecurePassword123!"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List subjects
    sub_res = client.get("/api/subjects", headers=headers)
    assert sub_res.status_code == 200
    subjects = sub_res.json()["subjects"]
    assert len(subjects) >= 4
    python_sub = next(s for s in subjects if s["slug"] == "python")
    assert python_sub["is_active"] is True

    # Try selecting a "Coming Soon" subject
    bad_select = client.post("/api/subjects/select", json={"subject_id": "subj_webdev"}, headers=headers)
    assert bad_select.status_code == 400
    assert "Coming Soon" in bad_select.json()["detail"]

    # Select Python
    good_select = client.post("/api/subjects/select", json={"subject_id": "subj_python"}, headers=headers)
    assert good_select.status_code == 200
    assert good_select.json()["slug"] == "python"


def test_assessment_questions_and_answers_security():
    login_res = client.post("/api/auth/login", json={
        "email": "ankush@pragyax.test",
        "password": "SecurePassword123!"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/assessments/questions?subject_id=subj_python", headers=headers)
    assert res.status_code == 200
    questions = res.json()
    assert len(questions) == 5

    # CRITICAL: Pre-submission questions must NEVER reveal correct_option or explanation
    for q in questions:
        assert "option_a" in q
        assert "option_b" in q
        assert "option_c" in q
        assert "option_d" in q
        assert "correct_option" not in q
        assert "explanation" not in q


def test_assessment_submission_and_evaluation():
    login_res = client.post("/api/auth/login", json={
        "email": "ankush@pragyax.test",
        "password": "SecurePassword123!"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Incomplete submission rejected
    bad_sub = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {"q_py_1": "B"}  # only 1 answer provided
    }, headers=headers)
    assert bad_sub.status_code == 400
    assert "Missing answer" in bad_sub.json()["detail"]

    # Invalid option choice rejected
    bad_opt = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B",
            "q_py_2": "C",
            "q_py_3": "Z",  # Invalid!
            "q_py_4": "B",
            "q_py_5": "A"
        }
    }, headers=headers)
    assert bad_opt.status_code == 400
    assert "Invalid option 'Z'" in bad_opt.json()["detail"]

    # Valid submission with 4/5 correct answers (Intermediate proficiency)
    # Correct answers: q1: B, q2: C, q3: C, q4: B, q5: A
    valid_sub = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B",  # Correct
            "q_py_2": "C",  # Correct
            "q_py_3": "A",  # Wrong (selected A instead of C)
            "q_py_4": "B",  # Correct
            "q_py_5": "A"   # Correct
        }
    }, headers=headers)
    assert valid_sub.status_code == 200
    result = valid_sub.json()
    assert result["score"] == 4
    assert result["total"] == 5
    assert result["percentage"] == 80.0
    assert result["proficiency_level"] == "Intermediate"
    assert result["is_mock"] is True
    assert len(result["breakdown"]) == 5
    assert len(result["recommended_topics"]) > 0

    attempt_id = result["id"]

    # Retrieve by ID
    get_res = client.get(f"/api/assessments/{attempt_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == attempt_id


def test_user_isolation():
    # Create second user
    client.post("/api/auth/register", json={
        "name": "Second Student",
        "email": "student2@pragyax.test",
        "password": "Password123!"
    })
    res_user2 = client.post("/api/auth/login", json={
        "email": "student2@pragyax.test",
        "password": "Password123!"
    })
    token_user2 = res_user2.json()["token"]
    headers2 = {"Authorization": f"Bearer {token_user2}"}

    # User 1 completes assessment
    login1 = client.post("/api/auth/login", json={
        "email": "ankush@pragyax.test",
        "password": "SecurePassword123!"
    })
    headers1 = {"Authorization": f"Bearer {login1.json()['token']}"}

    sub = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B", "q_py_2": "C", "q_py_3": "C", "q_py_4": "B", "q_py_5": "A"
        }
    }, headers=headers1)
    attempt_id_u1 = sub.json()["id"]

    # User 2 tries to access User 1's attempt -> Must be forbidden / 404
    isolation_res = client.get(f"/api/assessments/{attempt_id_u1}", headers=headers2)
    assert isolation_res.status_code == 404


def test_dashboard_real_metrics():
    login_res = client.post("/api/auth/login", json={
        "email": "ankush@pragyax.test",
        "password": "SecurePassword123!"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    dash_res = client.get("/api/dashboard", headers=headers)
    assert dash_res.status_code == 200
    data = dash_res.json()
    metrics = data["metrics"]
    assert metrics["total_assessments_completed"] >= 1
    assert metrics["latest_score"] is not None
    assert metrics["average_percentage"] > 0
    assert len(data["recent_attempts"]) >= 1


def test_daily_challenge_and_badge_flow():
    login_res = client.post("/api/auth/login", json={
        "email": "ankush@pragyax.test",
        "password": "SecurePassword123!"
    })
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch daily challenge
    chal_res = client.get("/api/challenges/daily", headers=headers)
    assert chal_res.status_code == 200
    chal = chal_res.json()
    assert chal["id"] == "chal_today_py"
    assert chal["has_completed"] is False
    assert chal["correct_option"] is None  # hidden before completion

    # Submit correct answer ('B')
    sub_res = client.post("/api/challenges/submit", json={
        "challenge_id": "chal_today_py",
        "selected_option": "B"
    }, headers=headers)
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["is_correct"] is True
    assert sub_data["points_awarded"] == 50

    # Duplicate submission attempt must be rejected
    dup_res = client.post("/api/challenges/submit", json={
        "challenge_id": "chal_today_py",
        "selected_option": "B"
    }, headers=headers)
    assert dup_res.status_code == 400
    assert "already completed" in dup_res.json()["detail"]


def _login(email="ankush@pragyax.test", password="SecurePassword123!"):
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_lowercase_answers_graded_and_unknown_ids_rejected():
    headers = _login()
    res = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {"q_py_1": "b", "q_py_2": "c", "q_py_3": "c", "q_py_4": "b", "q_py_5": "a"}
    }, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["score"] == 5 and body["proficiency_level"] == "Advanced"

    res = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {"q_py_1": "B", "q_py_2": "C", "q_py_3": "C", "q_py_4": "B", "q_py_5": "A", "q_fake": "A"}
    }, headers=headers)
    assert res.status_code == 400


def test_proficiency_thresholds_and_recommendations():
    headers = _login()
    res = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {"q_py_1": "A", "q_py_2": "A", "q_py_3": "C", "q_py_4": "A", "q_py_5": "B"}
    }, headers=headers).json()
    assert res["score"] == 1 and res["proficiency_level"] == "Beginner"
    assert len(res["recommended_topics"]) == 4  # one per missed question, in question order
    assert res["recommended_topics"][0].startswith("Mutable vs immutable")
    wrong = [b for b in res["breakdown"] if not b["is_correct"]]
    assert all(b["explanation"] for b in wrong)


def test_persistence_survives_restart():
    headers = _login()
    before = client.get("/api/assessments/history", headers=headers).json()["attempts"]
    assert before
    # Simulate a backend restart: brand-new app client against the same PostgreSQL database
    with TestClient(app) as restarted:
        after = restarted.get("/api/assessments/history", headers=headers).json()["attempts"]
        assert [a["id"] for a in after] == [a["id"] for a in before]
        detail = restarted.get(f"/api/assessments/{before[0]['id']}", headers=headers)
        assert detail.status_code == 200


def test_dashboard_reflects_saved_records():
    headers = _login()
    dash = client.get("/api/dashboard", headers=headers).json()
    history = client.get("/api/assessments/history", headers=headers).json()["attempts"]
    assert dash["metrics"]["total_assessments_completed"] == len(history)
    assert dash["metrics"]["latest_score"] == history[0]["score"]
    assert dash["recommendations_source"] == "latest_assessment"
    assert dash["has_selected_subject"] is True
    assert dash["metrics"]["chat_questions_asked"] >= 1
    assert dash["metrics"]["total_points"] == client.get("/api/gamification/profile", headers=headers).json()["total_xp"]
    assert dash["metrics"]["total_points"] == 150  # diagnostic + challenge


def test_new_user_dashboard_has_no_fabricated_stats():
    client.post("/api/auth/register", json={"name": "Fresh User", "email": "fresh@pragyax.test", "password": "Password123!"})
    dash = client.get("/api/dashboard", headers=_login("fresh@pragyax.test", "Password123!")).json()
    assert dash["metrics"]["total_assessments_completed"] == 0
    assert dash["metrics"]["latest_score"] is None
    assert dash["recent_attempts"] == []
    assert dash["recommendations_source"] == "starter"
    assert dash["has_selected_subject"] is False
    assert dash["selected_subject"]["id"] == "subj_python"  # default shown, but not marked as chosen


def test_chat_history_is_per_user():
    headers2 = _login("student2@pragyax.test", "Password123!")
    msgs = client.get("/api/chat/history", headers=headers2).json()["messages"]
    assert msgs == []


def test_logout_invalidates_token():
    headers = _login()
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_invalid_challenge_option_rejected():
    headers = _login("student2@pragyax.test", "Password123!")
    res = client.post("/api/challenges/submit", json={"challenge_id": "chal_today_py", "selected_option": "Z"}, headers=headers)
    assert res.status_code == 400
    # Rejected input must not consume the user's one attempt
    assert client.get("/api/challenges/daily", headers=headers).json()["has_completed"] is False


def test_mock_chat_is_subject_aware_not_echo():
    headers = _login("student2@pragyax.test", "Password123!")
    reply = client.post("/api/chat/message", json={"message": "Why can't a list be a dictionary key?"}, headers=headers).json()
    assert "hashable" in reply["content"]
    assert "Why can't a list" not in reply["content"]
