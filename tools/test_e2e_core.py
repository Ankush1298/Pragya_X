import os
import sys
import uuid
import requests

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000/api")

def run():
    print(f"Connecting to PragyaX API at {BASE_URL}...")
    unique = uuid.uuid4().hex[:8]
    email = f"e2e_core_{unique}@example.com"
    username = f"e2e_{unique}"
    password = "StrongPassword123!"

    # 1. Registration
    print("\n[Step 1] Registering test user...")
    reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "name": username,
        "password": password
    })
    print(f"Registration response: {reg_resp.status_code}")
    assert reg_resp.status_code in (200, 201), f"Register failed: {reg_resp.text}"
    user_data = reg_resp.json()
    token = user_data.get("token") or user_data.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # 2. Login verification
    print("\n[Step 2] Logging in to verify credential validation & session persistence...")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    login_data = login_resp.json()
    token = login_data.get("token") or login_data.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Login successful! User ID: {login_data.get('user', {}).get('id', 'N/A')}")

    # 3. Learning Chat - Subject Selection
    print("\n[Step 3] Fetching learning subjects...")
    subj_resp = requests.get(f"{BASE_URL}/subjects", headers=headers)
    print(f"Subjects status: {subj_resp.status_code}")
    assert subj_resp.status_code == 200, f"Subjects failed: {subj_resp.text}"
    subjects = subj_resp.json().get("subjects", [])
    print(f"Found {len(subjects)} subjects. Selecting active subject...")
    active_subj = next((s for s in subjects if s.get("slug") == "python" or s.get("id") == "subj_python"), subjects[0])
    sel_resp = requests.post(f"{BASE_URL}/subjects/select", json={"subject_id": active_subj["id"]}, headers=headers)
    assert sel_resp.status_code == 200, f"Select subject failed: {sel_resp.text}"
    print(f"Selected subject: {active_subj.get('title')}")

    # 4. Learning Chat - Create Chat Session
    print(f"\n[Step 4] Creating a learning chat for {active_subj['id']}...")
    chat_resp = requests.post(f"{BASE_URL}/learn/chats", json={"subject_id": active_subj["id"], "title": "Python Basics"}, headers=headers)
    assert chat_resp.status_code in (200, 201), f"Create chat failed: {chat_resp.text}"
    chat = chat_resp.json()
    chat_id = chat["id"]
    print(f"Chat created successfully! ID: {chat_id}")

    # 5. Learning Chat - Send Message & AI Response
    print("\n[Step 5] Submitting learning chat message...")
    msg_resp = requests.post(f"{BASE_URL}/learn/chats/{chat_id}/messages", json={"message": "Explain list comprehensions in Python", "mode": "explain"}, headers=headers)
    assert msg_resp.status_code in (200, 201), f"Send message failed: {msg_resp.text}"
    msg_data = msg_resp.json()
    ai_reply = msg_data.get("reply") or msg_data.get("content") or msg_data.get("message")
    print(f"AI response received: {str(ai_reply)[:100]}...")

    # 6. Assessment - Question Loading
    print("\n[Step 6] Loading assessment questions for Python...")
    quest_resp = requests.get(f"{BASE_URL}/assessments/questions?subject_id={active_subj['id']}", headers=headers)
    assert quest_resp.status_code == 200, f"Assessment load failed: {quest_resp.text}"
    questions = quest_resp.json()
    print(f"Loaded {len(questions)} assessment questions.")
    assert len(questions) >= 5, f"Expected at least 5 questions, got {len(questions)}"

    # 7. Assessment - Answer Selection & Submission
    print("\n[Step 7] Submitting assessment answers...")
    answers = {}
    for q in questions[:5]:
        answers[q["id"]] = "A"
    
    sub_resp = requests.post(f"{BASE_URL}/assessments/submit", json={
        "subject_id": active_subj["id"],
        "answers": answers
    }, headers=headers)
    assert sub_resp.status_code in (200, 201), f"Submit assessment failed: {sub_resp.text}"
    result_data = sub_resp.json()
    print(f"Assessment evaluated! Score: {result_data.get('score')}/{result_data.get('total')}, Percentage: {result_data.get('percentage')}%, Level: {result_data.get('proficiency_level')}")

    # 8. Assessment History / Saved Results
    print("\n[Step 8] Verifying saved assessment history...")
    hist_resp = requests.get(f"{BASE_URL}/assessments/history", headers=headers)
    assert hist_resp.status_code == 200, f"Get assessment history failed: {hist_resp.text}"
    history = hist_resp.json()
    attempts = history.get("attempts", [])
    print(f"Assessment history verified. Record count: {len(attempts)}")
    assert len(attempts) > 0, "Expected at least 1 saved attempt in history"

    # 9. Dashboard Data Refresh
    print("\n[Step 9] Verifying user dashboard data refresh...")
    dash_resp = requests.get(f"{BASE_URL}/dashboard", headers=headers)
    assert dash_resp.status_code == 200, f"Dashboard failed: {dash_resp.text}"
    dash_data = dash_resp.json()
    print(f"Dashboard verified! XP: {dash_data.get('stats', {}).get('total_xp', dash_data.get('xp'))}, Rank: {dash_data.get('stats', {}).get('rank', 'N/A')}")

    print("\n==========================================")
    print("ALL CORE LEARNING JOURNEY STEPS PASSED 100%!")
    print("==========================================")

if __name__ == "__main__":
    run()
