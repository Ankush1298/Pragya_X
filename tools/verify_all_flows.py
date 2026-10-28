"""
Comprehensive End-to-End Flow Verification Script for PragyaX-Latest
Tests:
1. Project submission, persistence, and portfolio update.
2. Two independent users completing a full 1v1 battle.
3. Referral qualification requiring initial assessment AND first eligible mission.
4. Hosted college/company competition lifecycle (org -> create -> submit -> leaderboard -> winners -> cert).
5. Certificate download and public verification.
6. Notification delivery and read/unread state.
"""

import os
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
import uuid
import httpx

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000/api")

client = httpx.Client(base_url=BASE_URL, timeout=30.0)

def register_user(email: str, name: str, password: str = "TestPassword123!"):
    resp = client.post("/auth/register", json={
        "email": email,
        "name": name,
        "password": password
    })
    assert resp.status_code in (200, 201), f"Register failed: {resp.text}"
    data = resp.json()
    token = data["token"]
    user = data["user"]
    return user, token

def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}

def run_all_verifications():
    print("=" * 70)
    print("STARTING PRAGYAX END-TO-END FLOW VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # TEST 1: Project Submission, Persistence, and Portfolio Update
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Project Submission, Persistence, and Portfolio Update...")
    u1, t1 = register_user(f"proj_user_{uuid.uuid4().hex[:6]}@example.com", "Project Learner")
    h1 = auth_headers(t1)

    # Fetch projects
    resp = client.get("/learn/projects", headers=h1)
    assert resp.status_code == 200, f"List projects failed: {resp.text}"
    projects = resp.json()["projects"]
    assert len(projects) > 0, "No projects returned"
    proj = projects[0]
    pid = proj["id"]
    print(f"  Selected project: {proj['title']} (id: {pid}) with {len(proj['milestones'])} milestones")

    # Mark all milestones done
    for idx in range(len(proj["milestones"])):
        resp = client.post(f"/learn/projects/{pid}/milestones", json={"index": idx, "done": True}, headers=h1)
        assert resp.status_code == 200, f"Milestone {idx} failed: {resp.text}"
    print("  All milestones marked completed.")

    # Submit project
    rubric_scores = {c: 3 for c in proj["rubric"]}
    submit_payload = {
        "text": "Implemented a fully decoupled clean architecture microservice with PostgreSQL backend and thorough automated tests.",
        "url": "https://github.com/example/pragyax-project-submission",
        "rubric_scores": rubric_scores
    }
    resp = client.post(f"/learn/projects/{pid}/submit", json=submit_payload, headers=h1)
    assert resp.status_code == 200, f"Project submit failed: {resp.text}"
    submitted_proj = resp.json()
    assert submitted_proj["status"] == "submitted"
    print("  Project successfully submitted.")

    # Verify portfolio update via skill-profile
    resp = client.get("/learn/skill-profile", headers=h1)
    assert resp.status_code == 200, f"Skill profile failed: {resp.text}"
    profile = resp.json()
    portfolio_projects = profile["projects"]
    matching = [p for p in portfolio_projects if p["id"] == pid]
    assert len(matching) == 1, f"Project {pid} not found in skill-profile portfolio: {portfolio_projects}"
    assert matching[0]["evidence_type"] == "self-assessed"
    assert matching[0]["rubric_total"] == 3 * len(proj["rubric"])
    print(f"  Verified portfolio update: project '{matching[0]['title']}' present with rubric score {matching[0]['rubric_total']}/{matching[0]['rubric_max']}.")

    # Verify project notification
    resp = client.get("/notifications", headers=h1)
    assert resp.status_code == 200
    notifs = resp.json()["notifications"]
    proj_notifs = [n for n in notifs if n.get("category") == "project" or "Project submitted" in n.get("title", "")]
    assert len(proj_notifs) > 0, "No project submission notification found"
    print(f"  Verified notification generated: '{proj_notifs[0]['title']}'")
    print("  -> TEST 1 PASSED.")

    # -------------------------------------------------------------------------
    # TEST 2: Two Independent Users Completing a Full 1v1 Battle
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Two Independent Users Completing a Full 1v1 Battle...")
    u_alice, t_alice = register_user(f"alice_{uuid.uuid4().hex[:6]}@example.com", "Alice Fighter")
    u_bob, t_bob = register_user(f"bob_{uuid.uuid4().hex[:6]}@example.com", "Bob Competitor")
    h_alice = auth_headers(t_alice)
    h_bob = auth_headers(t_bob)

    # Alice sends battle invite to Bob
    resp = client.post("/battles/invite", json={
        "recipient_identifier": u_bob["email"],
        "subject_id": "subj_python"
    }, headers=h_alice)
    assert resp.status_code == 200, f"Invite failed: {resp.text}"
    invite_data = resp.json()
    invitation_id = invite_data["invitation"]["id"]
    print(f"  Alice sent battle invitation {invitation_id} to Bob.")

    # Bob checks invitations
    resp = client.get("/battles/invitations", headers=h_bob)
    assert resp.status_code == 200
    b_invites = resp.json()
    assert any(i["id"] == invitation_id for i in b_invites), "Bob did not receive invitation"

    # Bob accepts invitation
    resp = client.post("/battles/invite/respond", json={
        "invitation_id": invitation_id,
        "accept": True
    }, headers=h_bob)
    assert resp.status_code == 200, f"Accept failed: {resp.text}"
    battle_info = resp.json()
    battle_id = battle_info["battle_id"]
    print(f"  Bob accepted. Battle created: {battle_id}")

    # Both ready up
    resp = client.post(f"/battles/{battle_id}/ready", headers=h_alice)
    assert resp.status_code == 200
    resp = client.post(f"/battles/{battle_id}/ready", headers=h_bob)
    assert resp.status_code == 200
    print("  Both players readied up.")

    # Verify battle is ACTIVE and fetch questions
    resp = client.get(f"/battles/{battle_id}", headers=h_alice)
    assert resp.status_code == 200
    state_alice = resp.json()
    assert state_alice["status"] == "ACTIVE"
    questions = state_alice["questions"]
    assert len(questions) > 0, "No battle questions returned"
    print(f"  Battle active with {len(questions)} questions.")

    # Alice submits answers (all 'A')
    alice_answers = {q["question_id"]: "A" for q in questions}
    resp = client.post(f"/battles/{battle_id}/submit", json={
        "battle_id": battle_id,
        "answers": alice_answers,
        "time_taken_seconds": 15
    }, headers=h_alice)
    assert resp.status_code == 200, f"Alice submit failed: {resp.text}"
    print("  Alice submitted answers.")

    # Check state after Alice submit: still ACTIVE, viewer_submitted = True
    resp = client.get(f"/battles/{battle_id}", headers=h_alice)
    assert resp.json()["viewer_submitted"] is True
    assert resp.json()["status"] == "ACTIVE"

    # Bob submits answers (all 'B')
    bob_answers = {q["question_id"]: "B" for q in questions}
    resp = client.post(f"/battles/{battle_id}/submit", json={
        "battle_id": battle_id,
        "answers": bob_answers,
        "time_taken_seconds": 18
    }, headers=h_bob)
    assert resp.status_code == 200, f"Bob submit failed: {resp.text}"
    print("  Bob submitted answers.")

    # Battle should now be COMPLETED
    resp = client.get(f"/battles/{battle_id}", headers=h_alice)
    assert resp.status_code == 200
    completed_state = resp.json()
    assert completed_state["status"] == "COMPLETED"
    result = completed_state["result"]
    assert result is not None
    print(f"  Battle completed! Outcome: {result['outcome']}, Winner: {result.get('winner_name') or 'TIE'}")
    assert len(result["scores"]) == 2
    assert len(completed_state["review"]) == len(questions)
    print("  Verified answer review and score breakdown.")

    # Verify leaderboard includes participants
    resp = client.get("/battles/leaderboard/ranking")
    assert resp.status_code == 200
    lb = resp.json()
    print(f"  Battle leaderboard has {len(lb)} ranked players.")
    print("  -> TEST 2 PASSED.")

    # -------------------------------------------------------------------------
    # TEST 3: Referral Qualification Requiring BOTH Diagnostic AND First Mission
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Referral Qualification (Requires Initial Assessment AND First Mission)...")
    u_ref_owner, t_ref_owner = register_user(f"refowner_{uuid.uuid4().hex[:6]}@example.com", "Referral Ambassador")
    h_ref_owner = auth_headers(t_ref_owner)

    # Get referral code
    resp = client.get("/referrals/dashboard", headers=h_ref_owner)
    assert resp.status_code == 200, f"Get referral dashboard failed: {resp.text}"
    ref_code = resp.json()["referral_code"]
    print(f"  Referral code generated: {ref_code}")

    # Register referee
    u_referee, t_referee = register_user(f"referee_{uuid.uuid4().hex[:6]}@example.com", "Referred Student")
    h_referee = auth_headers(t_referee)

    # Apply referral code
    resp = client.post("/referrals/apply", json={"referral_code": ref_code}, headers=h_referee)
    assert resp.status_code == 200, f"Apply referral failed: {resp.text}"
    apply_data = resp.json()
    assert apply_data["referral"]["status"] == "PENDING"
    print("  Referral code applied, status is PENDING.")

    # Check referrer dashboard: should show 1 pending, 0 rewarded
    resp = client.get("/referrals/dashboard", headers=h_ref_owner)
    summary = resp.json()
    assert summary["pending_referrals"] == 1
    assert summary["successful_referrals"] == 0
    print("  Referrer dashboard confirms 1 pending, 0 successful.")

    # STEP 3A: Referee completes ONLY diagnostic assessment
    # Start chat
    resp = client.post("/learn/chats", json={"subject_id": "subj_python"}, headers=h_referee)
    assert resp.status_code in (200, 201), f"Create chat failed: {resp.text}"
    chat_id = resp.json()["id"]

    # Fetch assessment questions
    resp = client.get(f"/learn/chats/{chat_id}/assessment", headers=h_referee)
    assert resp.status_code == 200, f"Get assessment failed: {resp.text}"
    diag_qs = resp.json()["questions"]
    diag_answers = {q["id"]: "A" for q in diag_qs}

    # Submit diagnostic assessment
    resp = client.post(f"/learn/chats/{chat_id}/assessment", json={"answers": diag_answers}, headers=h_referee)
    assert resp.status_code == 200, f"Submit assessment failed: {resp.text}"
    print("  Referee completed initial assessment diagnostic.")

    # VERIFY: Referral must STILL be PENDING! (Because first mission is NOT done yet)
    resp = client.get("/referrals/dashboard", headers=h_ref_owner)
    summary_mid = resp.json()
    assert summary_mid["pending_referrals"] == 1, f"Referral qualified prematurely before mission: {summary_mid}"
    assert summary_mid["successful_referrals"] == 0, f"Referral rewarded prematurely before mission: {summary_mid}"
    print("  CONFIRMED: Referral correctly remains PENDING after diagnostic alone!")

    # STEP 3B: Referee now completes the first learning mission
    # Get chat state with roadmap
    resp = client.get(f"/learn/chats/{chat_id}", headers=h_referee)
    assert resp.status_code == 200
    chat_state = resp.json()
    modules = chat_state["roadmap"]["modules"]
    assert len(modules) > 0, "No modules in roadmap"
    mod_id = modules[0]["id"]

    # Get module details and correct practice answers from curriculum
    from backend.app.services import curriculum
    mod_content = curriculum.get_module(mod_id)
    practice_answers = {q["id"]: q["answer"] for q in mod_content["questions"]}

    # Submit practice to complete first module
    resp = client.post(f"/learn/chats/{chat_id}/modules/{mod_id}/practice", json={"answers": practice_answers}, headers=h_referee)
    assert resp.status_code == 200, f"Practice submit failed: {resp.text}"
    practice_res = resp.json()
    assert practice_res["passed"] is True
    print(f"  Referee completed first learning mission module {mod_id} with score {practice_res['percentage']}%.")

    # VERIFY: Referral is NOW QUALIFIED and REWARDED!
    resp = client.get("/referrals/dashboard", headers=h_ref_owner)
    summary_done = resp.json()
    assert summary_done["pending_referrals"] == 0, f"Pending still > 0: {summary_done}"
    assert summary_done["successful_referrals"] == 1, f"Successful not 1: {summary_done}"
    assert summary_done["xp_earned_from_referrals"] == 150
    print("  CONFIRMED: Referral successfully transitioned to REWARDED! Referrer earned 150 XP.")

    # Check referee also got welcome bonus in XP ledger
    resp = client.get("/gamification/ledger", headers=h_referee)
    assert resp.status_code == 200
    ref_ledger = resp.json()
    ref_welcome = [e for e in ref_ledger if e.get("source_type") == "referral"]
    assert len(ref_welcome) > 0, "Referee welcome bonus not found in ledger"
    print(f"  Referee received welcome bonus: +{ref_welcome[0]['points_delta']} XP ({ref_welcome[0]['reason']}).")
    print("  -> TEST 3 PASSED.")

    # -------------------------------------------------------------------------
    # TEST 4 & 5: Hosted Competition Lifecycle & Certificate Verification
    # -------------------------------------------------------------------------
    print("\n[TEST 4 & 5] Testing Hosted Competition Lifecycle and Certificate Download/Verification...")
    # Admin user
    u_admin, t_admin = register_user(f"admin_{uuid.uuid4().hex[:6]}@example.com", "Platform Admin")
    h_admin = auth_headers(t_admin)

    # Student participant
    u_student, t_student = register_user(f"student_{uuid.uuid4().hex[:6]}@example.com", "Championship Contestant")
    h_student = auth_headers(t_student)

    # Register host organization (STUDENT orgs are auto-verified)
    resp = client.post("/competitions/organizations", json={
        "name": "Apex Engineering Student Chapter",
        "org_type": "STUDENT",
        "domain": "apex.edu",
        "description": "Student competition host chapter"
    }, headers=h_admin)
    assert resp.status_code == 200, f"Org create failed: {resp.text}"
    org_id = resp.json()["organization"]["id"]
    print(f"  Organization registered: {org_id}")

    # Create competition
    questions_payload = [
        {
            "question_text": "What is the time complexity of lookup in a Python hash table on average?",
            "topic": "Python Internals",
            "option_a": "O(1)",
            "option_b": "O(n)",
            "option_c": "O(log n)",
            "option_d": "O(n^2)",
            "correct_option": "A",
            "explanation": "Hash table lookups take O(1) on average due to direct key hashing.",
            "points": 20
        },
        {
            "question_text": "Which clause is used in PostgreSQL for UPSERT operations?",
            "topic": "PostgreSQL",
            "option_a": "ON DUPLICATE KEY",
            "option_b": "ON CONFLICT DO UPDATE",
            "option_c": "MERGE WHEN MATCHED",
            "option_d": "REPLACE INTO",
            "correct_option": "B",
            "explanation": "PostgreSQL standard syntax is ON CONFLICT (...) DO UPDATE.",
            "points": 20
        }
    ]

    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    start_time = (now - datetime.timedelta(hours=1)).isoformat()
    end_time = (now + datetime.timedelta(hours=24)).isoformat()

    resp = client.post("/competitions/create", json={
        "org_id": org_id,
        "title": "National Python Championship 2026",
        "description": "Annual competitive collegiate coding challenge.",
        "subject_id": "subj_python",
        "difficulty": "ADVANCED",
        "start_time": start_time,
        "end_time": end_time,
        "questions": questions_payload,
        "eligibility_rules": "Undergraduate students"
    }, headers=h_admin)
    assert resp.status_code == 200, f"Create comp failed: {resp.text}"
    comp_id = resp.json()["competition"]["id"]
    print(f"  Competition created: {comp_id}")

    # Student opens competition
    resp = client.get(f"/competitions/{comp_id}", headers=h_student)
    assert resp.status_code == 200
    comp_view = resp.json()
    assert comp_view["title"] == "National Python Championship 2026"
    assert len(comp_view["questions"]) == 2
    # Verify answer keys are hidden from student
    for q in comp_view["questions"]:
        assert "correct_option" not in q or q.get("correct_option") is None, "Answer key leaked in student view!"
    print("  Student fetched competition questions (answer keys properly masked).")

    # Student submits answers
    student_answers = {q["id"]: "A" if i == 0 else "B" for i, q in enumerate(comp_view["questions"])}
    resp = client.post(f"/competitions/{comp_id}/submit", json={
        "answers": student_answers,
        "time_taken_seconds": 45
    }, headers=h_student)
    assert resp.status_code == 200, f"Comp submit failed: {resp.text}"
    sub_res = resp.json()
    assert sub_res["score"] == 2
    assert sub_res["percentage"] == 100
    print(f"  Student submitted answers: Score {sub_res['score']}/{sub_res['total_questions']}, {sub_res['percentage']}%")

    # Check competition leaderboard
    resp = client.get(f"/competitions/{comp_id}/leaderboard")
    assert resp.status_code == 200
    comp_lb = resp.json()
    assert len(comp_lb) >= 1
    assert comp_lb[0]["user_name"] == "Championship Contestant"
    print(f"  Leaderboard reflects student ranking #1.")

    # Organizer dashboard check
    resp = client.get(f"/competitions/{comp_id}/dashboard", headers=h_admin)
    assert resp.status_code == 200
    dash = resp.json()
    assert dash["analytics"]["total_participants"] >= 1
    print(f"  Organizer dashboard shows {dash['analytics']['total_participants']} submissions.")

    # Announce winners and issue certificate
    resp = client.post(f"/competitions/{comp_id}/announce-winners", headers=h_admin)
    assert resp.status_code == 200, f"Announce winners failed: {resp.text}"
    announcement = resp.json()
    assert announcement["status"] == "ANNOUNCED"
    cert = announcement["certificate"]
    assert cert is not None
    verification_id = cert["verification_id"]
    print(f"  Winners announced! Certificate issued with verification ID: {verification_id}")

    # TEST 5: Public Certificate Verification and Download
    # Public verify without any auth
    resp = client.get(f"/certificates/verify/{verification_id}")
    assert resp.status_code == 200, f"Public verify failed: {resp.text}"
    public_cert = resp.json()
    assert public_cert["is_valid"] is True
    assert public_cert["recipient_name"] == "Championship Contestant"
    assert public_cert["verification_id"] == verification_id
    print("  Public verification succeeded: signature verified, recipient verified.")

    # Certificate download endpoint
    resp = client.get(f"/certificates/{verification_id}/download")
    assert resp.status_code == 200, f"Download failed: {resp.text}"
    assert "text/html" in resp.headers.get("content-type", "")
    html_content = resp.text
    assert verification_id in html_content
    assert "Championship Contestant" in html_content
    print("  Printable certificate HTML successfully generated and verified.")

    # Share card endpoint
    resp = client.get(f"/certificates/{verification_id}/share")
    assert resp.status_code == 200
    share_data = resp.json()
    assert "verification_url" in share_data
    assert "share_text" in share_data
    print("  Shareable card data successfully retrieved.")
    print("  -> TEST 4 & 5 PASSED.")

    # -------------------------------------------------------------------------
    # TEST 6: Notification Delivery and Read/Unread State
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing Notification Delivery and Read/Unread State...")
    # Check student notifications (should have competition winner notification)
    resp = client.get("/notifications", headers=h_student)
    assert resp.status_code == 200
    n_data = resp.json()
    initial_unread = n_data["unread"]
    notifs = n_data["notifications"]
    print(f"  Student has {len(notifs)} total notifications, {initial_unread} unread.")
    assert initial_unread > 0, "Expected at least one unread notification"
    unread_item = next(n for n in notifs if not n.get("read_at"))
    unread_id = unread_item["id"]

    # Mark single notification as read
    resp = client.post(f"/notifications/read?notification_id={unread_id}", headers=h_student)
    assert resp.status_code == 200
    new_unread = resp.json()["unread"]
    assert new_unread == initial_unread - 1
    print(f"  Marked notification {unread_id} read. Unread count decreased to {new_unread}.")

    # Mark all read
    resp = client.post("/notifications/read", headers=h_student)
    assert resp.status_code == 200
    assert resp.json()["unread"] == 0
    print("  Marked all notifications as read. Unread count is now 0.")

    # Test notification preferences update
    prefs_payload = {
        "battles": True,
        "achievements": True,
        "reminders": False,
        "projects": True,
        "quiet_start": "22:00",
        "quiet_end": "07:00"
    }
    resp = client.put("/notifications/preferences", json=prefs_payload, headers=h_student)
    assert resp.status_code == 200
    saved_prefs = resp.json()
    assert saved_prefs["reminders"] is False
    assert saved_prefs["quiet_start"] == "22:00"
    assert saved_prefs["quiet_end"] == "07:00"
    print("  Notification preferences updated and verified.")
    print("  -> TEST 6 PASSED.")

    print("\n" + "=" * 70)
    print("ALL END-TO-END FLOW VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_all_verifications()
