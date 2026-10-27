"""
Test Gamification and Admin Management (Sections D & G)
Validates unified XP system, level progression, badges, reward store redemptions,
admin organization approvals, referral abuse audits, and competition analytics.
"""

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.connection import init_db, get_db
from backend.app.database.competition_repository import CompetitionRepository

client = TestClient(app)


import uuid

def _setup_student_with_xp(name: str, email: str, points: int):
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
    uid = user_res.json()["id"]

    # Award points via ledger
    CompetitionRepository.record_xp_event(
        user_id=uid,
        event_key=f"init_xp.{uid}",
        points=points,
        reason="Initial learning activities",
        source_type="learning",
        source_id="init"
    )
    return {"token": token, "user_id": uid, "headers": {"Authorization": f"Bearer {token}"}}


def setup_module():
    init_db()


def test_gamification_profile_and_level_progression():
    student = _setup_student_with_xp("Level Climber", "climber@pragyax.test", points=350)

    res = client.get("/api/gamification/profile", headers=student["headers"])
    assert res.status_code == 200
    prof = res.json()
    assert prof["total_xp"] >= 350
    assert prof["level"] >= 3  # Level 3 threshold is 250 XP
    assert prof["title"] == "Logic Practitioner"
    assert "badges" in prof
    assert "streak" in prof


def test_reward_catalog_and_redemption_flow():
    # User with 500 XP
    student = _setup_student_with_xp("Shop Patron", "patron@pragyax.test", points=500)

    # View catalog with affordability
    cat_res = client.get("/api/gamification/rewards", headers=student["headers"])
    assert cat_res.status_code == 200
    catalog = cat_res.json()
    assert len(catalog) >= 3

    # Sticker pack costs 200 XP -> can_afford is True
    sticker_item = next(i for i in catalog if i["id"] == "rwd_swag_sticker")
    assert sticker_item["can_afford"] is True

    # Session costs 1000 XP -> can_afford is False
    session_item = next(i for i in catalog if i["id"] == "rwd_mentor_session")
    assert session_item["can_afford"] is False

    # Attempt to redeem session -> must fail with 400 (insufficient XP)
    bad_redeem = client.post("/api/gamification/rewards/redeem", json={"reward_id": "rwd_mentor_session"}, headers=student["headers"])
    assert bad_redeem.status_code == 400
    assert "insufficient xp" in bad_redeem.json()["detail"].lower()

    # Redeem stickers (200 XP) -> succeeds
    good_redeem = client.post("/api/gamification/rewards/redeem", json={"reward_id": "rwd_swag_sticker"}, headers=student["headers"])
    assert good_redeem.status_code == 200
    red_data = good_redeem.json()
    assert red_data["status"] == "CONFIRMED"
    assert red_data["xp_spent"] == 200
    assert red_data["remaining_xp"] == 300

    # Ledger reflects deduction
    ledger_res = client.get("/api/gamification/ledger", headers=student["headers"])
    assert ledger_res.status_code == 200
    ledger = ledger_res.json()
    assert any(e["points_delta"] == -200 for e in ledger)


def test_admin_competition_management_and_analytics(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "super_admin@pragyax.test")
    # Create admin user
    client.post("/api/auth/register", json={
        "name": "Super Admin",
        "email": "super_admin@pragyax.test",
        "password": "Password123!"
    })

    admin_token = client.post("/api/auth/login", json={
        "email": "super_admin@pragyax.test",
        "password": "Password123!"
    }).json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Non-admin accessing admin endpoints is 403 Forbidden
    student = _setup_student_with_xp("Regular Guy", "guy@pragyax.test", points=100)
    forbid = client.get("/api/admin/competitions/analytics", headers=student["headers"])
    assert forbid.status_code == 403

    # 2. Admin analytics
    analytics_res = client.get("/api/admin/competitions/analytics", headers=admin_headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert "competitions" in analytics
    assert "battles" in analytics
    assert "gamification" in analytics

    # 3. Admin audits
    ref_audit = client.get("/api/admin/competitions/audit/referrals", headers=admin_headers)
    assert ref_audit.status_code == 200
    assert isinstance(ref_audit.json(), list)

    rwd_audit = client.get("/api/admin/competitions/audit/rewards", headers=admin_headers)
    assert rwd_audit.status_code == 200
    assert isinstance(rwd_audit.json(), list)
