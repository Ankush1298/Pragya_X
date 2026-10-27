"""
Test College and Company Hosted Challenges (Section C)
Validates organization registration, admin approval, challenge scheduling,
eligibility, submissions, server-side grading, rankings, and organizer dashboards.
"""

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.connection import init_db

client = TestClient(app)


def _register_user(name: str, email: str):
    client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "Password123!"
    })
    token = client.post("/api/auth/login", json={
        "email": email,
        "password": "Password123!"
    }).json()["token"]
    user_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    return {"Authorization": f"Bearer {token}", "user": user_res.json(), "token": token}


def setup_module():
    init_db()


def _inside_window(monkeypatch):
    """Competition windows in these tests are 2026-11-01 10:00-14:00Z; pin 'now' inside it."""
    from datetime import datetime, timezone
    from backend.app.services import hosted_competition_service as hcs
    monkeypatch.setattr(hcs, "_now", lambda: datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc))



def test_organization_registration_and_verification_rules(monkeypatch):
    _inside_window(monkeypatch)
    organizer = _register_user("Prof. Sharma", "prof_sharma@iitd.ac.in")

    # Register college organization (pending verification)
    reg_org = client.post("/api/competitions/organizations", json={
        "name": "IIT Delhi Competitive Coding",
        "org_type": "COLLEGE",
        "domain": "iitd.ac.in",
        "description": "Annual Inter-College Hackathon Series"
    }, headers={"Authorization": f"Bearer {organizer['token']}"})
    assert reg_org.status_code == 200
    org = reg_org.json()["organization"]
    org_id = org["id"]
    assert org["is_verified"] == 0

    # Attempt to host official challenge before verification -> must be rejected
    sample_q = [{
        "question_text": "What does GIL stand for in CPython?",
        "option_a": "Global Interpreter Lock",
        "option_b": "General Instruction Loop",
        "option_c": "Generic Interface Level",
        "option_d": "Graphical Integration Library",
        "correct_option": "A"
    }]
    bad_create = client.post("/api/competitions/create", json={
        "org_id": org_id,
        "title": "IIT-D Annual Algorithm Clash",
        "description": "Premier inter-college coding tournament",
        "subject_id": "subj_python",
        "difficulty": "Hard",
        "start_time": "2026-11-01T10:00:00Z",
        "end_time": "2026-11-01T14:00:00Z",
        "questions": sample_q
    }, headers={"Authorization": f"Bearer {organizer['token']}"})
    assert bad_create.status_code == 400
    assert "pending administrative verification" in bad_create.json()["detail"].lower()

    # Admin verifies the organization
    admin = _register_user("System Admin", "admin@pragyax.test")
    # Mark user as admin in DB or verify directly via repository
    from backend.app.database.competition_repository import CompetitionRepository
    CompetitionRepository.verify_organization(org_id, is_verified=True)

    # Now creation succeeds!
    good_create = client.post("/api/competitions/create", json={
        "org_id": org_id,
        "title": "IIT-D Annual Algorithm Clash",
        "description": "Premier inter-college coding tournament",
        "subject_id": "subj_python",
        "difficulty": "Hard",
        "start_time": "2026-11-01T10:00:00Z",
        "end_time": "2026-11-01T14:00:00Z",
        "questions": sample_q
    }, headers={"Authorization": f"Bearer {organizer['token']}"})
    assert good_create.status_code == 200
    comp_id = good_create.json()["competition"]["id"]

    # Student competes
    student = _register_user("Contestant Rahul", "rahul_contest@pragyax.test")
    comp_view = client.get(f"/api/competitions/{comp_id}", headers={"Authorization": f"Bearer {student['token']}"}).json()
    assert "correct_option" not in comp_view["questions"][0]  # Hidden

    # Student submits answer
    q_id = comp_view["questions"][0]["id"]
    sub_res = client.post(f"/api/competitions/{comp_id}/submit", json={
        "answers": {q_id: "A"},
        "time_taken_seconds": 24.0
    }, headers={"Authorization": f"Bearer {student['token']}"})
    assert sub_res.status_code == 200
    assert sub_res.json()["score"] == 1
    assert sub_res.json()["percentage"] == 100.0

    # Check leaderboard
    lb_res = client.get(f"/api/competitions/{comp_id}/leaderboard")
    assert lb_res.status_code == 200
    lb = lb_res.json()
    assert len(lb) == 1
    assert lb[0]["user_name"] == "Contestant Rahul"
    assert lb[0]["rank"] == 1

    # Organizer views dashboard
    dash_res = client.get(f"/api/competitions/{comp_id}/dashboard", headers={"Authorization": f"Bearer {organizer['token']}"})
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["analytics"]["total_participants"] == 1
    assert dash_data["analytics"]["average_score"] == 1.0

    # Announce winners and issue certificate
    win_res = client.post(f"/api/competitions/{comp_id}/announce-winners", headers={"Authorization": f"Bearer {organizer['token']}"})
    assert win_res.status_code == 200
    win_data = win_res.json()
    assert win_data["status"] == "ANNOUNCED"
    assert "PRAGYA-CERT" in win_data["certificate"]["verification_id"]
