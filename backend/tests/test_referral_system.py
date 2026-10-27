"""
Test Referral System (Section E)
Validates unique referral codes, manual entry, anti-abuse checks, pending state,
mission qualification, idempotent XP awards, and dashboard metrics.
"""

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.connection import init_db

client = TestClient(app)


import uuid

def _register(name: str, email: str):
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
    user_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    return {"Authorization": f"Bearer {token}", "user": user_res.json(), "token": token}


def setup_module():
    init_db()


def test_referral_code_generation_and_anti_abuse():
    referrer = _register("Ambassador Priya", "priya_refer@pragyax.test")

    # 1. Referrer fetches unique code
    code_res = client.get("/api/referrals/my-code", headers={"Authorization": f"Bearer {referrer['token']}"})
    assert code_res.status_code == 200
    ref_code = code_res.json()["referral_code"]
    assert "PRAGYA-" in ref_code

    # 2. Anti-abuse: Self-referral must be rejected
    self_res = client.post("/api/referrals/apply", json={"referral_code": ref_code}, headers={"Authorization": f"Bearer {referrer['token']}"})
    assert self_res.status_code == 400
    assert "self-referral" in self_res.json()["detail"].lower()

    # 3. Anti-abuse: Invalid code must be rejected
    referee = _register("Newcomer Karan", "karan_new@pragyax.test")
    bad_res = client.post("/api/referrals/apply", json={"referral_code": "INVALID-CODE-999"}, headers={"Authorization": f"Bearer {referee['token']}"})
    assert bad_res.status_code == 400
    assert "invalid referral code" in bad_res.json()["detail"].lower()

    # 4. Valid application -> PENDING status, 0 rewards granted yet!
    apply_res = client.post("/api/referrals/apply", json={"referral_code": ref_code}, headers={"Authorization": f"Bearer {referee['token']}"})
    assert apply_res.status_code == 200
    assert apply_res.json()["status"] == "PENDING"

    # 5. Anti-abuse: Duplicate application rejected (only one referrer per student)
    dup_apply = client.post("/api/referrals/apply", json={"referral_code": ref_code}, headers={"Authorization": f"Bearer {referee['token']}"})
    assert dup_apply.status_code == 400
    assert "already has an active or completed referral" in dup_apply.json()["detail"].lower()

    # 6. Verify Dashboard shows 1 pending referral and 0 XP earned so far
    dash_pre = client.get("/api/referrals/dashboard", headers={"Authorization": f"Bearer {referrer['token']}"}).json()
    assert dash_pre["total_invited"] == 1
    assert dash_pre["pending_referrals"] == 1
    assert dash_pre["successful_referrals"] == 0
    assert dash_pre["xp_earned_from_referrals"] == 0


def test_referral_qualification_after_learning_milestone():
    referrer = _register("Mentor Suresh", "suresh_refer@pragyax.test")
    code_res = client.get("/api/referrals/my-code", headers={"Authorization": f"Bearer {referrer['token']}"})
    code = code_res.json()["referral_code"]

    referee = _register("Student Meera", "meera_referee@pragyax.test")
    client.post("/api/referrals/apply", json={"referral_code": code}, headers={"Authorization": f"Bearer {referee['token']}"})

    # Referee completes qualifying learning activity: Assessment
    sub_res = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B",
            "q_py_2": "C",
            "q_py_3": "C",
            "q_py_4": "B",
            "q_py_5": "A"
        }
    }, headers={"Authorization": f"Bearer {referee['token']}"})
    assert sub_res.status_code == 200

    # Product rule: an assessment alone must NOT qualify the referral
    dash_mid = client.get("/api/referrals/dashboard", headers={"Authorization": f"Bearer {referrer['token']}"}).json()
    assert dash_mid["successful_referrals"] == 0 and dash_mid["xp_earned_from_referrals"] == 0
    assert dash_mid["referral_history"][0]["status"] == "PENDING"

    # ...the first learning mission (module practice passed) completes the rule
    from backend.tests.learning_helpers import complete_first_mission
    complete_first_mission(client, {"Authorization": f"Bearer {referee['token']}"})

    dash_post = client.get("/api/referrals/dashboard", headers={"Authorization": f"Bearer {referrer['token']}"}).json()
    assert dash_post["successful_referrals"] >= 1
    assert dash_post["xp_earned_from_referrals"] >= 150
    assert dash_post["referral_history"][0]["status"] == "REWARDED"
    assert "referee_email" not in dash_post["referral_history"][0]

    # Referrer's XP ledger reflects referral award
    ledger_res = client.get("/api/gamification/ledger", headers={"Authorization": f"Bearer {referrer['token']}"})
    assert ledger_res.status_code == 200
    ledger = ledger_res.json()
    ref_event = next((e for e in ledger if e["source_type"] == "referral"), None)
    assert ref_event is not None
    assert ref_event["points_delta"] == 150
