"""
PragyaX Demonstration Journeys (Section H)
End-to-End Automated Demonstration of Ankush's Two Core Mission Journeys:

JOURNEY 1:
Student A challenges Student B → B accepts → both compete → results saved →
winner determined → XP awarded once → certificate issued → battle history and leaderboard updated.

JOURNEY 2:
New student enters referral code → referral pending → learning milestone completed →
referral successful → eligible reward awarded.
"""

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.connection import init_db

client = TestClient(app)


import uuid

def _create_user(name: str, email: str):
    unique_email = f"{uuid.uuid4().hex[:6]}_{email}"
    client.post("/api/auth/register", json={
        "name": name,
        "email": unique_email,
        "password": "SecurePassword123!"
    })
    token = client.post("/api/auth/login", json={
        "email": unique_email,
        "password": "SecurePassword123!"
    }).json()["token"]
    user_data = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return {"token": token, "user": user_data, "headers": {"Authorization": f"Bearer {token}"}}


def setup_module():
    init_db()


def test_journey_1_battle_to_certificate_and_leaderboard():
    """
    JOURNEY 1 DEMONSTRATION:
    Student A challenges Student B → B accepts → both compete → results saved →
    winner determined → XP awarded once → certificate issued → battle history and leaderboard updated.
    """
    # Step 1: Initialize Student A and Student B
    student_a = _create_user("Arjun Mehta", "arjun_demo@pragyax.test")
    student_b = _create_user("Bhavna Rao", "bhavna_demo@pragyax.test")

    # Step 2: Student A challenges Student B
    invite_res = client.post("/api/battles/invite", json={
        "recipient_identifier": student_b["user"]["email"],
        "subject_id": "subj_python"
    }, headers=student_a["headers"])
    assert invite_res.status_code == 200, f"Invitation failed: {invite_res.text}"
    inv_id = invite_res.json()["invitation"]["id"]
    assert invite_res.json()["invitation"]["status"] == "PENDING"

    # Step 3: Student B receives and accepts invitation
    b_invitations = client.get("/api/battles/invitations", headers=student_b["headers"]).json()
    assert any(inv["id"] == inv_id for inv in b_invitations)

    accept_res = client.post("/api/battles/invite/respond", json={
        "invitation_id": inv_id,
        "accept": True
    }, headers=student_b["headers"])
    assert accept_res.status_code == 200
    battle_id = accept_res.json()["battle_id"]
    assert battle_id.startswith("btl_")

    # Step 4: Both enter lobby and ready up
    view_a_init = client.get(f"/api/battles/{battle_id}", headers=student_a["headers"]).json()
    assert view_a_init["status"] == "CREATED"
    assert view_a_init["opponent_display_name"] == "Bhavna Rao"

    ready_a = client.post(f"/api/battles/{battle_id}/ready", headers=student_a["headers"])
    assert ready_a.status_code == 200

    ready_b = client.post(f"/api/battles/{battle_id}/ready", headers=student_b["headers"])
    assert ready_b.status_code == 200
    assert ready_b.json()["battle"]["status"] == "ACTIVE"

    # Step 5: Both compete and submit answers
    # Questions from seed: Python assessment question answers: B, C, C, B, A
    q_ids = [q["question_id"] for q in view_a_init["questions"]]

    # Student A answers 5/5 correctly
    answers_a = {q_ids[0]: "B", q_ids[1]: "C", q_ids[2]: "C", q_ids[3]: "B", q_ids[4]: "A"}
    sub_a = client.post(f"/api/battles/{battle_id}/submit", json={
        "battle_id": battle_id,
        "answers": answers_a,
        "time_taken_seconds": 18.2
    }, headers=student_a["headers"])
    assert sub_a.status_code == 200
    assert sub_a.json()["viewer_submitted"] is True
    # Masked before opponent finishes
    assert sub_a.json()["result"] is None

    # Student B answers 2/5 correctly
    answers_b = {q_ids[0]: "B", q_ids[1]: "A", q_ids[2]: "D", q_ids[3]: "B", q_ids[4]: "D"}
    sub_b = client.post(f"/api/battles/{battle_id}/submit", json={
        "battle_id": battle_id,
        "answers": answers_b,
        "time_taken_seconds": 22.0
    }, headers=student_b["headers"])
    assert sub_b.status_code == 200

    # Step 6: Server determines winner and saves results
    final_view = sub_b.json()
    assert final_view["status"] == "COMPLETED"
    assert final_view["result"]["outcome"] == "WIN"
    assert final_view["result"]["winner_user_id"] == student_a["user"]["id"]

    # Step 7: XP awarded once idempotently (Winner: 100 XP, Loser: 25 XP)
    ledger_a = client.get("/api/gamification/ledger", headers=student_a["headers"]).json()
    battle_xp_a = [e for e in ledger_a if e["source_type"] == "battle" and e["source_id"] == battle_id]
    assert len(battle_xp_a) == 1, "XP must be awarded exactly once for this battle"
    assert battle_xp_a[0]["points_delta"] == 100

    ledger_b = client.get("/api/gamification/ledger", headers=student_b["headers"]).json()
    battle_xp_b = [e for e in ledger_b if e["source_type"] == "battle" and e["source_id"] == battle_id]
    assert len(battle_xp_b) == 1
    assert battle_xp_b[0]["points_delta"] == 25

    # Step 8: Certificate issued to winner
    certs_a = client.get("/api/certificates/my-certificates", headers=student_a["headers"]).json()
    assert len(certs_a) >= 1
    winner_cert = certs_a[0]
    assert winner_cert["cert_type"] == "BATTLE_WINNER"
    assert "PRAGYA-CERT" in winner_cert["verification_id"]

    # Verify certificate cryptographically via public endpoint
    verif = client.get(f"/api/certificates/verify/{winner_cert['verification_id']}").json()
    assert verif["is_valid"] is True
    assert verif["recipient_name"] == "Arjun Mehta"

    # Step 9: Battle history & leaderboard updated
    history_a = client.get("/api/battles/my-battles", headers=student_a["headers"]).json()
    assert len(history_a) == 1
    assert history_a[0]["you_won"] is True

    leaderboard = client.get("/api/battles/leaderboard/ranking").json()
    arjun_entry = next((e for e in leaderboard if e["user_id"] == student_a["user"]["id"]), None)
    assert arjun_entry is not None
    assert arjun_entry["wins"] >= 1
    assert arjun_entry["win_streak"] >= 1


def test_journey_2_referral_to_milestone_and_reward():
    """
    JOURNEY 2 DEMONSTRATION:
    New student enters referral code → referral pending →
    learning milestone completed → referral successful → eligible reward awarded.
    """
    # Step 1: Existing student generates referral code
    mentor = _create_user("Sneha Kapoor", "sneha_demo@pragyax.test")
    code_res = client.get("/api/referrals/my-code", headers=mentor["headers"]).json()
    referral_code = code_res["referral_code"]
    assert "PRAGYA-" in referral_code

    # Step 2: New student registers and enters referral code during onboarding
    new_student = _create_user("Dev Patel", "dev_demo@pragyax.test")
    apply_res = client.post("/api/referrals/apply", json={"referral_code": referral_code}, headers=new_student["headers"])
    assert apply_res.status_code == 200

    # Step 3: Referral is in PENDING state; NO reward awarded yet!
    mentor_dash_init = client.get("/api/referrals/dashboard", headers=mentor["headers"]).json()
    assert mentor_dash_init["pending_referrals"] == 1
    assert mentor_dash_init["successful_referrals"] == 0
    assert mentor_dash_init["xp_earned_from_referrals"] == 0

    mentor_ledger_init = client.get("/api/gamification/ledger", headers=mentor["headers"]).json()
    assert not any(e["source_type"] == "referral" for e in mentor_ledger_init)

    # Step 4: New student completes learning milestone (First Assessment with passing score)
    assess_res = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B",
            "q_py_2": "C",
            "q_py_3": "C",
            "q_py_4": "B",
            "q_py_5": "A"
        }
    }, headers=new_student["headers"])
    assert assess_res.status_code == 200

    # Step 5: assessment alone keeps the referral PENDING (rule: assessment AND first learning mission)
    mid = client.get("/api/referrals/dashboard", headers=mentor["headers"]).json()
    assert mid["pending_referrals"] == 1 and mid["successful_referrals"] == 0

    from backend.tests.learning_helpers import complete_first_mission
    complete_first_mission(client, new_student["headers"])
    mentor_dash_final = client.get("/api/referrals/dashboard", headers=mentor["headers"]).json()
    assert mentor_dash_final["pending_referrals"] == 0
    assert mentor_dash_final["successful_referrals"] == 1
    assert mentor_dash_final["xp_earned_from_referrals"] == 150

    # Step 6: Referrer receives 150 XP and Referee receives 50 XP in their respective ledgers
    mentor_ledger = client.get("/api/gamification/ledger", headers=mentor["headers"]).json()
    mentor_ref_reward = next(e for e in mentor_ledger if e["source_type"] == "referral")
    assert mentor_ref_reward["points_delta"] == 150

    new_student_ledger = client.get("/api/gamification/ledger", headers=new_student["headers"]).json()
    new_ref_reward = next(e for e in new_student_ledger if e["source_type"] == "referral")
    assert new_ref_reward["points_delta"] == 50


def test_journey_a_learning_complete_flow():
    """
    JOURNEY A DEMONSTRATION (Core Learning Lifecycle):
    Register → Login → Subject Catalog → Assessment Questions → Submit Answers → Result Calculation → Dashboard Update.
    """
    # 1. Register and Login student
    learner = _create_user("Aarav Sharma", "aarav_learn@pragyax.test")

    # 2. View subject catalog
    subjects_res = client.get("/api/subjects", headers=learner["headers"])
    assert subjects_res.status_code == 200
    subjects = subjects_res.json()["subjects"]
    assert len(subjects) >= 1
    py_subj = next((s for s in subjects if s["id"] == "subj_python"), None)
    assert py_subj is not None
    assert py_subj["title"] == "Python Programming"

    # 3. Fetch assessment questions (answers hidden)
    questions_res = client.get("/api/assessments/questions?subject_id=subj_python", headers=learner["headers"])
    assert questions_res.status_code == 200
    q_data = questions_res.json()
    assert len(q_data) == 5
    for q in q_data:
        assert "correct_option" not in q
        assert "id" in q
        assert "question_text" in q

    # 4. Submit assessment with answers (4/5 correct)
    answers = {
        "q_py_1": "B",  # Correct
        "q_py_2": "C",  # Correct
        "q_py_3": "C",  # Correct
        "q_py_4": "B",  # Correct
        "q_py_5": "B"   # Incorrect (Correct is A)
    }
    submit_res = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": answers
    }, headers=learner["headers"])
    assert submit_res.status_code == 200
    res_data = submit_res.json()
    assert res_data["score"] == 4
    assert res_data["total"] == 5
    assert res_data["percentage"] == 80.0
    assert "summary_feedback" in res_data
    assert "breakdown" in res_data

    # 5. Verify learner's Dashboard reflects completion and stats
    dash_res = client.get("/api/dashboard", headers=learner["headers"])
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["user"]["name"] == "Aarav Sharma"
    assert dash["metrics"]["total_assessments_completed"] >= 1
    assert dash["metrics"]["latest_percentage"] >= 80.0
    assert len(dash["recent_attempts"]) >= 1


def test_journey_d_challenges_flow():
    """
    JOURNEY D DEMONSTRATION (Challenge Lifecycle):
    Student joins daily challenge → submits answer → score evaluated → streak updated →
    duplicate submission rejected → leaderboard verified.
    """
    challenger = _create_user("Diya Sen", "diya_chal@pragyax.test")

    # 1. Fetch challenge library and daily challenge
    daily_res = client.get("/api/challenges/daily", headers=challenger["headers"])
    assert daily_res.status_code == 200
    daily = daily_res.json()
    assert "id" in daily
    assert "title" in daily

    # 2. Submit challenge answer (chal_py_01 correct option is B)
    chal_id = "chal_py_01"
    sub_res = client.post("/api/challenges/submit", json={
        "challenge_id": chal_id,
        "selected_option": "B"
    }, headers=challenger["headers"])
    assert sub_res.status_code == 200
    result = sub_res.json()
    assert result["challenge_id"] == chal_id
    assert "is_correct" in result
    assert "points_awarded" in result

    # 3. Duplicate submission rejected
    dup_res = client.post("/api/challenges/submit", json={
        "challenge_id": chal_id,
        "selected_option": "B"
    }, headers=challenger["headers"])
    assert dup_res.status_code in (400, 409)
    assert "already completed" in dup_res.json()["detail"].lower()

    # 4. Check user challenge streak and history
    streak_res = client.get("/api/challenges/streak", headers=challenger["headers"])
    assert streak_res.status_code == 200
    assert streak_res.json()["current_streak"] >= 1

    # 5. Verify challenge leaderboard includes challenger
    lb_res = client.get("/api/challenges/leaderboard?limit=50", headers=challenger["headers"])
    assert lb_res.status_code == 200
    lb = lb_res.json()
    assert any(entry["user_id"] == challenger["user"]["id"] for entry in lb)


def _inside_window(monkeypatch, day=1, month=11):
    """Pin the competition clock inside the test window (10:00-18:00Z on the given day)."""
    from datetime import datetime, timezone
    from backend.app.services import hosted_competition_service as hcs
    monkeypatch.setattr(hcs, "_now", lambda: datetime(2026, month, day, 11, 0, tzinfo=timezone.utc))



def test_journey_e_hosted_competitions_flow(monkeypatch):
    _inside_window(monkeypatch, 10, 11)
    """
    JOURNEY E DEMONSTRATION (Hosted Competitions Lifecycle):
    Authorized organizer creates competition → student joins/submits →
    result calculated → rankings generated → organizer concludes competition.
    """
    organizer = _create_user("Dean Kapoor", "dean_iit@iitb.ac.in")

    # 1. Register organization and verify
    reg_org = client.post("/api/competitions/organizations", json={
        "name": "IIT Bombay Computing Society",
        "org_type": "COLLEGE",
        "domain": "iitb.ac.in",
        "description": "National Hackathon"
    }, headers=organizer["headers"]).json()
    org_id = reg_org["organization"]["id"]

    from backend.app.database.competition_repository import CompetitionRepository
    CompetitionRepository.verify_organization(org_id, is_verified=True)

    # 2. Organizer schedules competition with questions
    comp_create = client.post("/api/competitions/create", json={
        "org_id": org_id,
        "title": "IITB All-India Code Sprint",
        "description": "Prestigious inter-college showdown",
        "subject_id": "subj_python",
        "difficulty": "Hard",
        "start_time": "2026-11-10T10:00:00Z",
        "end_time": "2026-11-10T18:00:00Z",
        "questions": [{
            "question_text": "Which data structure uses LIFO order?",
            "option_a": "Queue",
            "option_b": "Stack",
            "option_c": "Array",
            "option_d": "Tree",
            "correct_option": "B"
        }]
    }, headers=organizer["headers"])
    assert comp_create.status_code == 200
    comp_id = comp_create.json()["competition"]["id"]

    # 3. Student joins and submits answers
    student = _create_user("Kavita Nair", "kavita_comp@pragyax.test")
    comp_view = client.get(f"/api/competitions/{comp_id}", headers=student["headers"]).json()
    q_id = comp_view["questions"][0]["id"]

    sub_res = client.post(f"/api/competitions/{comp_id}/submit", json={
        "answers": {q_id: "B"},
        "time_taken_seconds": 15.5
    }, headers=student["headers"])
    assert sub_res.status_code == 200
    assert sub_res.json()["score"] == 1
    assert sub_res.json()["percentage"] == 100.0

    # 4. View leaderboard / rankings
    lb_res = client.get(f"/api/competitions/{comp_id}/leaderboard")
    assert lb_res.status_code == 200
    rankings = lb_res.json()
    assert len(rankings) >= 1
    assert rankings[0]["user_id"] == student["user"]["id"]
    assert rankings[0]["rank"] == 1

    # 5. Organizer checks dashboard and announces winners
    dash_res = client.get(f"/api/competitions/{comp_id}/dashboard", headers=organizer["headers"])
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["analytics"]["total_participants"] >= 1

    announce_res = client.post(f"/api/competitions/{comp_id}/announce-winners", headers=organizer["headers"])
    assert announce_res.status_code == 200
    assert announce_res.json()["status"] == "ANNOUNCED"
