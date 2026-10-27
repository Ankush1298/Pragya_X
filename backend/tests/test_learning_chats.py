"""Chat-scoped learning engine, notifications, referral rule, admin allow-list, production config."""
import os
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.connection import init_db
from backend.app.services import curriculum
from backend.tests.learning_helpers import register, new_chat, diagnostic, pass_module, complete_first_mission

client = TestClient(app)


def setup_module():
    init_db()


def xp(headers):
    return client.get("/api/gamification/profile", headers=headers).json()["total_xp"]


def test_chats_are_isolated_per_subject_and_per_user():
    a, _ = register(client, "Ada")
    b, _ = register(client, "Bob")
    py = new_chat(client, a, "subj_python")
    bio = new_chat(client, a, "subj_biology")
    assert py["id"] != bio["id"] and bio["subject_title"] == "Foundational Biology"

    client.post(f"/api/learn/chats/{py['id']}/messages", json={"message": "Explain list comprehensions"}, headers=a)
    msgs = client.get(f"/api/learn/chats/{py['id']}/messages", headers=a).json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert client.get(f"/api/learn/chats/{bio['id']}/messages", headers=a).json()["messages"] == []

    # diagnostics/roadmaps stay independent
    assert diagnostic(client, a, py["id"], "A").status_code == 200
    py_state = client.get(f"/api/learn/chats/{py['id']}", headers=a).json()
    bio_state = client.get(f"/api/learn/chats/{bio['id']}", headers=a).json()
    assert py_state["roadmap"]["modules"] and bio_state["roadmap"] is None and not bio_state["has_diagnostic"]

    # another user can neither read nor write them: 404, not 403 (no existence leak)
    for method, path, body in [("get", f"/api/learn/chats/{py['id']}", None),
                               ("get", f"/api/learn/chats/{py['id']}/messages", None),
                               ("post", f"/api/learn/chats/{py['id']}/messages", {"message": "hi"}),
                               ("get", f"/api/learn/chats/{py['id']}/assessment", None),
                               ("patch", f"/api/learn/chats/{py['id']}", {"title": "hacked"})]:
        r = getattr(client, method)(path, headers=b, **({"json": body} if body else {}))
        assert r.status_code == 404, (method, path, r.status_code)
    assert client.get("/api/learn/chats", headers=b).json()["chats"] == []
    assert client.get("/api/learn/chats").status_code == 401


def test_no_answer_keys_leak_before_submission():
    h, _ = register(client)
    c = new_chat(client, h)
    qs = client.get(f"/api/learn/chats/{c['id']}/assessment", headers=h).text
    assert "correct_option" not in qs and "explanation" not in qs
    diagnostic(client, h, c["id"], "A")
    first = client.get(f"/api/learn/chats/{c['id']}", headers=h).json()["current_module"]["id"]
    lesson = client.get(f"/api/learn/chats/{c['id']}/modules/{first}", headers=h).text
    assert '"answer"' not in lesson and "explanation" not in lesson


@pytest.mark.parametrize("sid", list(curriculum.CONTENT))
def test_every_curated_subject_runs_the_full_loop(sid):
    h, _ = register(client)
    c = new_chat(client, h, sid)
    assert diagnostic(client, h, c["id"], "A").json()["kind"] == "diagnostic"
    st = client.get(f"/api/learn/chats/{c['id']}", headers=h).json()
    assert st["weaknesses"] and st["roadmap"]["modules"] and st["current_module"]
    before = xp(h)
    r = pass_module(client, h, c["id"], st["current_module"]["id"]).json()
    assert r["module_completed"] and r["xp_awarded"] == 40
    assert xp(h) == before + 40
    after = client.get(f"/api/learn/chats/{c['id']}", headers=h).json()
    assert after["modules_completed"] == 1 and after["overall_progress"] > 0
    # idempotent: passing again never pays twice
    assert pass_module(client, h, c["id"], st["current_module"]["id"]).json()["xp_awarded"] == 0
    assert xp(h) == before + 40


def test_failed_practice_records_mistakes_then_revision_clears_after_pass():
    h, _ = register(client)
    c = new_chat(client, h)
    diagnostic(client, h, c["id"], "A")
    mid = client.get(f"/api/learn/chats/{c['id']}", headers=h).json()["current_module"]["id"]
    bad = pass_module(client, h, c["id"], mid, correct=False).json()
    assert not bad["module_completed"] and bad["xp_awarded"] == 0
    rev = client.get(f"/api/learn/chats/{c['id']}/revision", headers=h).json()
    assert len(rev["items"]) == 3 and rev["items"][0]["explanation"]
    assert pass_module(client, h, c["id"], mid).json()["module_completed"]
    assert client.get(f"/api/learn/chats/{c['id']}/revision", headers=h).json()["items"] == []


def test_prerequisites_and_validation_are_enforced():
    h, _ = register(client)
    c = new_chat(client, h)
    assert client.get(f"/api/learn/chats/{c['id']}/modules/mod_py_types", headers=h).status_code == 409  # no diagnostic yet
    diagnostic(client, h, c["id"], "A")
    assert client.get(f"/api/learn/chats/{c['id']}/modules/mod_py_async", headers=h).status_code in (404, 409)
    assert client.post(f"/api/learn/chats/{c['id']}/modules/mod_py_types/practice",
                       json={"answers": {"mod_py_types_p1": 0}}, headers=h).status_code == 400  # must answer all
    assert client.post(f"/api/learn/chats/{c['id']}/modules/mod_py_types/practice",
                       json={"answers": {"mod_py_types_p1": 9, "mod_py_types_p2": 0, "mod_py_types_p3": 0}}, headers=h).status_code == 400


def test_reassessment_shows_improvement_and_awards_no_second_xp():
    h, _ = register(client)
    c = new_chat(client, h, "subj_biology")
    diagnostic(client, h, c["id"], "A")
    base = xp(h)
    qs = client.get(f"/api/learn/chats/{c['id']}/assessment", headers=h).json()["questions"]
    keys = {q["id"]: q for q in __import__("backend.app.database.repository", fromlist=["Repository"]).Repository.get_raw_assessment_questions_with_answers("subj_biology")}
    again = client.post(f"/api/learn/chats/{c['id']}/assessment",
                        json={"answers": {q["id"]: keys[q["id"]]["correct_option"] for q in qs}}, headers=h).json()
    assert again["kind"] == "reassessment" and again["percentage"] == 100.0
    st = client.get(f"/api/learn/chats/{c['id']}", headers=h).json()
    assert st["improvement"]["delta"] > 0 and len(st["assessment_history"]) == 2
    assert xp(h) == base  # retakes measure growth, they don't farm XP


def test_custom_subject_is_honestly_limited():
    h, _ = register(client)
    c = client.post("/api/learn/chats", json={"custom_subject": "Medieval History"}, headers=h).json()
    assert c["curated"] is False and "No validated PragyaX curriculum" in c["limitation"]
    assert client.get(f"/api/learn/chats/{c['id']}/assessment", headers=h).status_code == 400
    m = client.post(f"/api/learn/chats/{c['id']}/messages", json={"message": "Who was Charlemagne?"}, headers=h).json()
    assert m["is_mock"] and "no knowledge" in (m["notice"] or "").lower()
    assert client.post("/api/learn/chats", json={}, headers=h).status_code == 400


def test_archive_rename_and_mentor_modes():
    h, _ = register(client)
    c = new_chat(client, h)
    assert client.patch(f"/api/learn/chats/{c['id']}", json={"title": "My Python"}, headers=h).json()["title"] == "My Python"
    hint = client.post(f"/api/learn/chats/{c['id']}/messages", json={"message": "help with slicing", "mode": "hint"}, headers=h).json()
    assert hint["notice"]  # mock mode is labelled honestly
    assert client.post(f"/api/learn/chats/{c['id']}/messages", json={"message": "x", "mode": "bogus"}, headers=h).status_code == 400
    client.patch(f"/api/learn/chats/{c['id']}", json={"archived": True}, headers=h)
    assert client.post(f"/api/learn/chats/{c['id']}/messages", json={"message": "hi"}, headers=h).status_code == 409
    assert client.get("/api/learn/chats", headers=h).json()["chats"] == []
    assert len(client.get("/api/learn/chats?include_archived=true", headers=h).json()["chats"]) == 1


def test_referral_needs_assessment_and_mission_and_late_codes_are_rejected():
    ref, _ = register(client, "Ref")
    code = client.get("/api/referrals/my-code", headers=ref).json()["referral_code"]
    new, _ = register(client, "New")
    assert client.post("/api/referrals/apply", json={"referral_code": code}, headers=new).status_code == 200
    c = new_chat(client, new)
    diagnostic(client, new, c["id"], "A")
    dash = client.get("/api/referrals/dashboard", headers=ref).json()
    assert dash["referral_history"][0]["status"] == "PENDING" and "first learning module" in dash["reward_rule"]
    mid = client.get(f"/api/learn/chats/{c['id']}", headers=new).json()["current_module"]["id"]
    pass_module(client, new, c["id"], mid)
    pass_module(client, new, c["id"], mid)
    dash = client.get("/api/referrals/dashboard", headers=ref).json()
    assert dash["referral_history"][0]["status"] == "REWARDED" and dash["xp_earned_from_referrals"] == 150
    ledger = client.get("/api/gamification/ledger", headers=ref).json()
    assert sum(1 for e in ledger if e["source_type"] == "referral") == 1  # rewarded once

    # an account that already finished a mission cannot retroactively attach a referrer
    late, _ = register(client, "Late")
    complete_first_mission(client, late)
    assert client.post("/api/referrals/apply", json={"referral_code": code}, headers=late).status_code == 400
    # self-referral
    own = client.get("/api/referrals/my-code", headers=late).json()["referral_code"]
    assert client.post("/api/referrals/apply", json={"referral_code": own}, headers=late).status_code == 400


def test_notifications_dedupe_preferences_and_isolation():
    a, _ = register(client, "Alice")
    b, b_email = register(client, "Bobby")
    inv = client.post("/api/battles/invite", json={"recipient_identifier": b_email, "subject_id": "subj_python"}, headers=a)
    assert inv.status_code == 200, inv.text
    n = client.get("/api/notifications", headers=b).json()
    assert n["unread"] == 1 and n["notifications"][0]["kind"] == "battle"
    assert client.get("/api/notifications", headers=a).json()["unread"] == 0   # sender not notified
    assert client.post("/api/notifications/read", headers=b).json()["unread"] == 0
    # opt-out suppresses future battle notifications
    assert client.put("/api/notifications/preferences", json={"battles": False}, headers=b).status_code == 200
    c, c_email = register(client, "Carol")
    client.put("/api/notifications/preferences", json={"battles": False}, headers=c)
    client.post("/api/battles/invite", json={"recipient_identifier": c_email, "subject_id": "subj_python"}, headers=a)
    assert client.get("/api/notifications", headers=c).json()["notifications"] == []
    assert client.put("/api/notifications/preferences", json={"quiet_start": "99:99"}, headers=b).status_code == 400
    # revision reminders: at most one per chat per day
    d, _ = register(client)
    ch = new_chat(client, d)
    diagnostic(client, d, ch["id"], "A")
    mid = client.get(f"/api/learn/chats/{ch['id']}", headers=d).json()["current_module"]["id"]
    pass_module(client, d, ch["id"], mid, correct=False)
    for _ in range(3):
        client.get("/api/notifications", headers=d)
    assert sum(1 for x in client.get("/api/notifications", headers=d).json()["notifications"] if x["kind"] == "revision") == 1


def test_projects_require_milestones_and_are_labelled_self_assessed():
    h, _ = register(client)
    pid = "proj_python_basic"
    proj = next(p for p in client.get("/api/learn/projects", headers=h).json()["projects"] if p["id"] == pid)
    scores = {c: 2 for c in proj["rubric"]}
    body = {"text": "I built the tracker and tested totals with edge cases.", "rubric_scores": scores}
    assert client.post(f"/api/learn/projects/{pid}/submit", json=body, headers=h).status_code == 409
    for i in range(len(proj["milestones"])):
        client.post(f"/api/learn/projects/{pid}/milestones", json={"index": i}, headers=h)
    done = client.post(f"/api/learn/projects/{pid}/submit", json=body, headers=h).json()
    assert done["status"] == "submitted" and "Self-assessed" in done["evaluation_note"]
    prof = client.get("/api/learn/skill-profile", headers=h).json()
    assert prof["projects"][0]["evidence_type"] == "self-assessed" and "accredited" in prof["disclaimer"]


def test_admin_is_an_env_allow_list_not_a_guessable_email(monkeypatch):
    import uuid
    ADMIN_LIKE = f"admin_{uuid.uuid4().hex[:6]}@pragyax.test"
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    client.post("/api/auth/register", json={"name": "Imposter", "email": ADMIN_LIKE, "password": "SecurePassword123!"})
    tok = client.post("/api/auth/login", json={"email": ADMIN_LIKE, "password": "SecurePassword123!"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/api/admin/competitions/analytics", headers=h).status_code == 403
    monkeypatch.setenv("ADMIN_EMAILS", ADMIN_LIKE)
    assert client.get("/api/admin/competitions/analytics", headers=h).status_code == 200


def test_production_config_fails_fast(monkeypatch):
    from backend.app.config import settings
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(type(settings), "SECRET_KEY", settings.INSECURE_DEV_SECRET, raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError) as e:
        settings.validate_production()
    msg = str(e.value)
    assert "SECRET_KEY" in msg and "DATABASE_URL" in msg


def test_certificate_html_escapes_user_supplied_names():
    from backend.app.services.certificate_service import CertificateService
    h, _ = register(client, "<script>alert(1)</script>")
    uid = client.get("/api/auth/me", headers=h).json()["id"]
    cert = CertificateService.issue_certificate(uid, "<script>alert(1)</script>", "ASSESSMENT", "T", "D", {"assessment_id": "x1"})
    html = CertificateService.render_downloadable_certificate_html(cert["verification_id"])["html"]
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html and "accredited" in html


def test_postgres_learning_schema_is_migrated():
    from backend.app.database.connection import get_db
    with get_db() as conn:
        cur=conn.cursor();cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        names={r['tablename'] for r in cur.fetchall()}
    assert {'learning_chats','learning_chat_messages','learning_module_progress','learning_practice_answers','notifications'} <= names


def test_login_is_throttled_after_repeated_failures():
    h, email = register(client)
    for _ in range(8):
        assert client.post("/api/auth/login", json={"email": email, "password": "wrong-pass"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "SecurePassword123!"}).status_code == 429


def test_register_with_referral_code_applies_it_and_bad_code_never_blocks_signup():
    ref, _ = register(client, "Inviter")
    code = client.get("/api/referrals/my-code", headers=ref).json()["referral_code"]
    ok = client.post("/api/auth/register", json={"name": "Friend", "email": "friend_%s@pragyax.test" % code[-4:].lower(),
                                                 "password": "SecurePassword123!", "referral_code": code})
    assert ok.status_code == 201 and "Referral code applied" in ok.json()["referral_notice"]
    bad = client.post("/api/auth/register", json={"name": "Other", "email": "other_%s@pragyax.test" % code[-4:].lower(),
                                                  "password": "SecurePassword123!", "referral_code": "NOPE-0000"})
    assert bad.status_code == 201 and "Invalid" in bad.json()["referral_notice"]
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + ok.json()["token"]}).json()["is_admin"] is False


def _competition_payload(org_id, start, end):
    return {"org_id": org_id, "title": "Window Test", "description": "d", "start_time": start, "end_time": end,
            "questions": [{"question_text": "2+2?", "option_a": "4", "option_b": "5", "option_c": "6", "option_d": "7",
                           "correct_option": "A"}]}


def test_competition_enforces_time_window_and_one_attempt():
    org_h, _ = register(client, "Organiser")
    stu, _ = register(client, "Contestant")
    org = client.post("/api/competitions/organizations", json={"name": "Study Club", "org_type": "STUDENT", "description": "x"}, headers=org_h)
    assert org.status_code in (200, 201), org.text
    oid = org.json().get("id") or org.json()["organization"]["id"]
    future = client.post("/api/competitions/create", json=_competition_payload(oid, "2099-01-01T10:00:00Z", "2099-01-02T10:00:00Z"), headers=org_h)
    assert future.status_code == 200, future.text
    cid = future.json().get("id") or future.json()["competition"]["id"]
    view = client.get(f"/api/competitions/{cid}", headers=stu).json()
    assert view["status"] == "SCHEDULED" and view["questions"] == []        # no peeking before the start
    assert client.post(f"/api/competitions/{cid}/submit", json={"answers": {}}, headers=stu).status_code == 400
    live = client.post("/api/competitions/create", json=_competition_payload(oid, "2020-01-01T10:00:00Z", "2099-01-02T10:00:00Z"), headers=org_h)
    lid = live.json().get("id") or live.json()["competition"]["id"]
    q = client.get(f"/api/competitions/{lid}", headers=stu).json()["questions"][0]
    assert "correct_option" not in q
    assert client.post(f"/api/competitions/{lid}/submit", json={"answers": {q["id"]: "A"}}, headers=stu).status_code == 200
    again = client.post(f"/api/competitions/{lid}/submit", json={"answers": {q["id"]: "A"}}, headers=stu)
    assert again.status_code == 400 and "already submitted" in again.json()["detail"]
    # only the organiser may see the organiser dashboard
    assert client.get(f"/api/competitions/{lid}/dashboard", headers=stu).status_code == 403
    assert client.get(f"/api/competitions/{lid}/dashboard", headers=org_h).status_code == 200


def test_battle_history_never_leaks_answer_keys_or_opponent_answers():
    a, a_email = register(client, "Duelist A")
    b, b_email = register(client, "Duelist B")
    inv = client.post("/api/battles/invite", json={"recipient_identifier": b_email}, headers=a).json()["invitation"]
    acc = client.post("/api/battles/invite/respond", json={"invitation_id": inv["id"], "accept": True}, headers=b)
    assert acc.status_code == 200, acc.text
    bid = acc.json().get("battle_id") or acc.json()["battle"]["id"]
    for h in (a, b):
        client.post(f"/api/battles/{bid}/ready", json={"battle_id": bid}, headers=h)
    raw = client.get("/api/battles/my-battles", headers=a).text
    for banned in ("correct_option", "questions_json", "explanation", "player_one_answers", "player_two_answers"):
        assert banned not in raw
    view = client.get(f"/api/battles/{bid}", headers=a).json()
    assert view["status"] == "ACTIVE" and "correct_option" not in str(view["questions"])
    qa = {q["question_id"]: "A" for q in view["questions"]}
    client.post(f"/api/battles/{bid}/submit", json={"battle_id": bid, "answers": qa}, headers=a)
    assert client.get(f"/api/battles/{bid}", headers=a).json()["result"] is None   # nothing revealed until both finish
    client.post(f"/api/battles/{bid}/submit", json={"battle_id": bid, "answers": qa}, headers=b)
    done = client.get(f"/api/battles/{bid}", headers=a).json()
    assert done["status"] == "COMPLETED" and done["result"]["outcome"] in ("TIE", "WIN")
    # result notification + XP landed for both
    assert any(n["title"] == "Battle result" for n in client.get("/api/notifications", headers=b).json()["notifications"])
    assert xp(a) > 0 and xp(b) > 0
