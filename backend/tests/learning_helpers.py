"""Shared helpers: drive the learning API like a student (answer keys come from the server-side curriculum)."""
import uuid

from backend.app.services import curriculum


def register(client, name="Learner", prefix="lrn"):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@pragyax.test"
    client.post("/api/auth/register", json={"name": name, "email": email, "password": "SecurePassword123!"})
    token = client.post("/api/auth/login", json={"email": email, "password": "SecurePassword123!"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}, email


def new_chat(client, headers, subject_id="subj_python", **kw):
    r = client.post("/api/learn/chats", json={"subject_id": subject_id, **kw}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def diagnostic(client, headers, chat_id, answer="A"):
    qs = client.get(f"/api/learn/chats/{chat_id}/assessment", headers=headers).json()["questions"]
    assert len(qs) == 5
    return client.post(f"/api/learn/chats/{chat_id}/assessment", json={"answers": {q["id"]: answer for q in qs}}, headers=headers)


def pass_module(client, headers, chat_id, module_id, correct=True):
    mod = curriculum.get_module(module_id)
    assert client.get(f"/api/learn/chats/{chat_id}/modules/{module_id}", headers=headers).status_code == 200
    answers = {q["id"]: (q["answer"] if correct else (q["answer"] + 1) % len(q["options"])) for q in mod["questions"]}
    return client.post(f"/api/learn/chats/{chat_id}/modules/{module_id}/practice", json={"answers": answers}, headers=headers)


def complete_first_mission(client, headers):
    chat = new_chat(client, headers)
    assert diagnostic(client, headers, chat["id"]).status_code == 200
    state = client.get(f"/api/learn/chats/{chat['id']}", headers=headers).json()
    first = state["current_module"]["id"]
    res = pass_module(client, headers, chat["id"], first)
    assert res.status_code == 200 and res.json()["module_completed"], res.text
    return chat["id"], first
