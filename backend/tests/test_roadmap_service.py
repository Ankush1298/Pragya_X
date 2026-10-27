"""
Test Suite for Personalized Learning Roadmap Service and API Endpoints
Owned by: Arsh (FastAPI Backend Architecture)
Covers Phase 2 Step 1 Foundation:
1. Deterministic roadmap generation
2. Weakness-based module selection
3. Prerequisite validation
4. Locked module behavior
5. Progress percentage calculation
6. Invalid progress transitions
7. Empty assessment results
8. Duplicate weakness topics
9. Unsupported subjects
10. API authentication enforcement
11. HTTP 501 behavior when persistence is unavailable
"""

import os
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database.connection import init_db
from backend.app.main import app
from backend.app.services.roadmap_service import (
    build_deterministic_roadmap,
    calculate_overall_progress,
    validate_module_prerequisites,
    update_module_lock_statuses,
    validate_module_completion,
    validate_progress_transition,
    validate_catalog_integrity,
    SubjectCatalogComingSoonError,
    PYTHON_CATALOG
)

init_db()




@pytest.fixture
def auth_client():
    """Creates a registered, authenticated TestClient session."""
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:8]
    email = f"roadmap_{suffix}@pragyax.test"
    reg_res = client.post("/api/auth/register", json={
        "name": f"Roadmap Student {suffix}",
        "email": email,
        "password": "RoadmapPassword123!"
    })
    token = reg_res.json()["token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    return client


# ===========================================================================
# Unit Tests: Roadmap Service Business Logic
# ===========================================================================

def test_deterministic_roadmap_generation_default():
    """1. Deterministic roadmap generation with default parameters."""
    roadmap = build_deterministic_roadmap(
        subject_id="subj_python",
        weaknesses=None,
        user_id="usr_test_123"
    )
    assert roadmap["subject_id"] == "subj_python"
    assert roadmap["user_id"] == "usr_test_123"
    assert len(roadmap["modules"]) >= 4
    # First module must have no prerequisites and be unlocked
    first_mod = roadmap["modules"][0]
    assert first_mod["prerequisite_module_ids"] == []
    assert first_mod["status"] == "unlocked"
    assert first_mod["completion_percentage"] == 0.0


def test_weakness_based_module_selection():
    """2. Weakness-based module selection targeted to assessment diagnostic."""
    weaknesses = ["Generators, Iterators & Memory Streaming"]
    roadmap = build_deterministic_roadmap(
        subject_id="subj_python",
        weaknesses=weaknesses,
        user_id="usr_test_123"
    )
    module_ids = [m["id"] for m in roadmap["modules"]]
    # Target module must be present
    assert "mod_py_generators" in module_ids
    # Its prerequisites (types, collections, functions, comprehensions) must be automatically included
    assert "mod_py_types" in module_ids
    assert "mod_py_comprehensions" in module_ids
    # Root module is unlocked, downstream generators module is locked
    gen_mod = next(m for m in roadmap["modules"] if m["id"] == "mod_py_generators")
    assert gen_mod["status"] == "locked"


def test_prerequisite_validation():
    """3. Prerequisite validation for module dependencies."""
    module_with_prereqs = {
        "id": "mod_py_collections",
        "prerequisite_module_ids": ["mod_py_types"]
    }
    # Unmet prerequisites
    assert validate_module_prerequisites(module_with_prereqs, set()) is False
    assert validate_module_prerequisites(module_with_prereqs, {"mod_other"}) is False
    # Met prerequisites
    assert validate_module_prerequisites(module_with_prereqs, {"mod_py_types"}) is True

    # Module without prerequisites is always valid
    root_module = {"id": "mod_py_types", "prerequisite_module_ids": []}
    assert validate_module_prerequisites(root_module, set()) is True


def test_locked_module_behavior_and_lock_updating():
    """4. Locked module behavior and lock state machine updating."""
    modules = [
        {"id": "mod_1", "prerequisite_module_ids": [], "completion_percentage": 0.0, "status": "locked"},
        {"id": "mod_2", "prerequisite_module_ids": ["mod_1"], "completion_percentage": 0.0, "status": "locked"},
        {"id": "mod_3", "prerequisite_module_ids": ["mod_2"], "completion_percentage": 0.0, "status": "locked"},
    ]
    # No completions: mod_1 unlocks because it has no prereqs; mod_2 and mod_3 stay locked
    res1 = update_module_lock_statuses(modules, completed_module_ids=set())
    assert res1[0]["status"] == "unlocked"
    assert res1[1]["status"] == "locked"
    assert res1[2]["status"] == "locked"

    # mod_1 completed: mod_1 is completed, mod_2 unlocks, mod_3 stays locked
    res2 = update_module_lock_statuses(modules, completed_module_ids={"mod_1"})
    assert res2[0]["status"] == "completed"
    assert res2[0]["completion_percentage"] == 100.0
    assert res2[1]["status"] == "unlocked"
    assert res2[2]["status"] == "locked"


def test_progress_percentage_calculation():
    """5. Overall progress percentage calculation across modules."""
    # Empty list
    assert calculate_overall_progress([]) == 0.0

    # Mixed progress
    modules = [
        {"completion_percentage": 100.0},
        {"completion_percentage": 50.0},
        {"completion_percentage": 0.0},
        {"completion_percentage": 0.0}
    ]
    # (100 + 50 + 0 + 0) / 4 = 37.5
    assert calculate_overall_progress(modules) == 37.5


def test_invalid_progress_transitions():
    """6. Invalid progress transitions rejected by state machine."""
    # Locked cannot jump to in_progress or completed
    with pytest.raises(ValueError, match="Cannot transition a locked module directly"):
        validate_progress_transition(
            current_status="locked", new_status="in_progress",
            current_percentage=0.0, new_percentage=20.0
        )

    with pytest.raises(ValueError, match="Cannot transition a locked module directly"):
        validate_progress_transition(
            current_status="locked", new_status="completed",
            current_percentage=0.0, new_percentage=100.0
        )

    # Locked cannot have >0% progress
    with pytest.raises(ValueError, match="Locked module cannot have progress greater than 0%"):
        validate_progress_transition(
            current_status="locked", new_status="locked",
            current_percentage=0.0, new_percentage=10.0
        )

    # Completed must be 100%
    with pytest.raises(ValueError, match="Completed module must have exactly 100% completion"):
        validate_progress_transition(
            current_status="in_progress", new_status="completed",
            current_percentage=50.0, new_percentage=95.0
        )

    # Completed cannot reset to locked
    with pytest.raises(ValueError, match="Completed module cannot be reset to locked"):
        validate_progress_transition(
            current_status="completed", new_status="locked",
            current_percentage=100.0, new_percentage=0.0
        )

    # Progress cannot decrease
    with pytest.raises(ValueError, match="Progress percentage cannot decrease"):
        validate_progress_transition(
            current_status="in_progress", new_status="in_progress",
            current_percentage=60.0, new_percentage=40.0
        )

    # Invalid status string
    with pytest.raises(ValueError, match="Invalid status 'invalid_status'"):
        validate_progress_transition(
            current_status="unlocked", new_status="invalid_status",
            current_percentage=0.0, new_percentage=10.0
        )

    # Valid transitions succeed
    assert validate_progress_transition("unlocked", "in_progress", 0.0, 25.0) is True
    assert validate_progress_transition("in_progress", "completed", 75.0, 100.0) is True


def test_empty_assessment_results_generates_foundational_roadmap():
    """7. Empty assessment results builds comprehensive foundational curriculum."""
    roadmap = build_deterministic_roadmap(subject_id="subj_python", weaknesses=[])
    assert len(roadmap["modules"]) >= 4
    assert "foundational" in roadmap["description"].lower()


def test_duplicate_weakness_topics_deduplicated():
    """8. Duplicate weakness topics deduplicated while preserving order."""
    weaknesses = [
        "Python Data Types & Mutability",
        "python data types & mutability",
        "Python Data Types & Mutability",
        "Generators, Iterators & Memory Streaming"
    ]
    roadmap = build_deterministic_roadmap(
        subject_id="subj_python",
        weaknesses=weaknesses,
        user_id="usr_dedup_test"
    )
    module_ids = [m["id"] for m in roadmap["modules"]]
    # mod_py_types should only appear once
    assert module_ids.count("mod_py_types") == 1
    assert "mod_py_generators" in module_ids


def test_unsupported_subjects_rejected():
    """9. Unsupported subjects raise descriptive ValueError."""
    with pytest.raises(ValueError, match="Unsupported subject 'subj_rust'"):
        build_deterministic_roadmap(subject_id="subj_rust", weaknesses=["ownership"])


# ===========================================================================
# API Integration Tests: Authentication & Safety Constraints
# ===========================================================================

def test_api_authentication_enforcement():
    """10. API authentication enforcement (HTTP 401 for missing/invalid tokens)."""
    unauth_client = TestClient(app)

    # GET /api/roadmap without token -> 401
    res1 = unauth_client.get("/api/roadmap")
    assert res1.status_code == 401

    # GET /api/roadmap/{module_id} without token -> 401
    res2 = unauth_client.get("/api/roadmap/mod_py_types")
    assert res2.status_code == 401

    # POST /api/roadmap/{module_id}/complete without token -> 401
    res3 = unauth_client.post("/api/roadmap/mod_py_types/complete", json={})
    assert res3.status_code == 401

    # Invalid token format -> 401
    res4 = unauth_client.get("/api/roadmap", headers={"Authorization": "InvalidTokenHeader"})
    assert res4.status_code == 401


def test_persistence_completion_success(auth_client):
    """11. Persistence completion returns HTTP 200 and progress is saved."""
    client = auth_client

    # Successfully complete unlocked module mod_py_types
    res = client.post("/api/roadmap/mod_py_types/complete", json={
        "status": "completed",
        "completion_percentage": 100.0
    })
    assert res.status_code == 200
    data = res.json()
    assert data["module_id"] == "mod_py_types"
    assert data["status"] == "completed"
    assert data["completion_percentage"] == 100.0
    assert data["updated_at"] is not None


def test_authenticated_roadmap_retrieval(auth_client):
    """Verifies that an authenticated learner can retrieve their personalized roadmap."""
    client = auth_client
    res = client.get("/api/roadmap")
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert "modules" in data
    assert len(data["modules"]) >= 4
    assert data["subject_id"] == "subj_python"

    # Fetch specific module details
    first_mod_id = data["modules"][0]["id"]
    mod_res = client.get(f"/api/roadmap/{first_mod_id}")
    assert mod_res.status_code == 200
    assert mod_res.json()["id"] == first_mod_id

    # Nonexistent module returns 404
    missing_res = client.get("/api/roadmap/mod_nonexistent_xyz")
    assert missing_res.status_code == 404


def test_subject_catalog_coming_soon(auth_client):
    """Phase 3: Supported subjects without an implemented catalog return HTTP 400 with 'coming soon'."""
    client = auth_client

    # Service layer raises SubjectCatalogComingSoonError
    with pytest.raises(SubjectCatalogComingSoonError, match="Roadmaps for this subject are coming soon."):
        build_deterministic_roadmap(subject_id="subj_js")

    with pytest.raises(SubjectCatalogComingSoonError, match="Roadmaps for this subject are coming soon."):
        build_deterministic_roadmap(subject_id="subj_react")

    # API query with subject_id=subj_js returns HTTP 400
    res_js = client.get("/api/roadmap?subject_id=subj_js")
    assert res_js.status_code == 400
    assert res_js.json()["detail"] == "Roadmaps for this subject are coming soon."

    # API query for specific module in non-catalog subject returns HTTP 400
    mod_js = client.get("/api/roadmap/mod_py_types?subject_id=subj_js")
    assert mod_js.status_code == 400
    assert mod_js.json()["detail"] == "Roadmaps for this subject are coming soon."


def test_prerequisite_graph_validation():
    """Phase 4: Prerequisite graph integrity, self-referential and cycle detection."""
    # 1. Valid Python catalog passes cleanly
    validate_catalog_integrity(PYTHON_CATALOG)

    # 2. Missing prerequisite module ID is detected
    broken_missing = {
        "mod_a": {
            "id": "mod_a",
            "prerequisite_module_ids": ["mod_nonexistent"]
        }
    }
    with pytest.raises(ValueError, match="references non-existent prerequisite 'mod_nonexistent'"):
        validate_catalog_integrity(broken_missing)

    # 3. Self-referential prerequisite is detected
    broken_self = {
        "mod_a": {
            "id": "mod_a",
            "prerequisite_module_ids": ["mod_a"]
        }
    }
    with pytest.raises(ValueError, match="Self-referential prerequisite detected in module 'mod_a'"):
        validate_catalog_integrity(broken_self)

    # 4. Circular dependency (Cycle) is detected
    broken_cycle = {
        "mod_a": {
            "id": "mod_a",
            "prerequisite_module_ids": ["mod_b"]
        },
        "mod_b": {
            "id": "mod_b",
            "prerequisite_module_ids": ["mod_c"]
        },
        "mod_c": {
            "id": "mod_c",
            "prerequisite_module_ids": ["mod_a"]
        }
    }
    with pytest.raises(ValueError, match="Circular dependency detected in prerequisite graph"):
        validate_catalog_integrity(broken_cycle)


def test_multi_user_isolation():
    """Phase 5: User A vs User B roadmap isolation, distinct IDs, and private attempt protection."""
    client = TestClient(app)

    # Register User Alpha
    suffix_a = uuid.uuid4().hex[:8]
    res_a = client.post("/api/auth/register", json={
        "name": f"User Alpha {suffix_a}",
        "email": f"alpha_{suffix_a}@pragyax.test",
        "password": "PasswordAlpha123!"
    })
    token_a = res_a.json()["token"]
    user_a_id = res_a.json()["user"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User Beta
    suffix_b = uuid.uuid4().hex[:8]
    res_b = client.post("/api/auth/register", json={
        "name": f"User Beta {suffix_b}",
        "email": f"beta_{suffix_b}@pragyax.test",
        "password": "PasswordBeta123!"
    })
    token_b = res_b.json()["token"]
    user_b_id = res_b.json()["user"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User Alpha takes assessment with weakness
    submit_res_a = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B",
            "q_py_2": "C",
            "q_py_3": "C",
            "q_py_4": "B",
            "q_py_5": "A"
        }
    }, headers=headers_a)
    attempt_a_id = submit_res_a.json()["id"]

    # 1 & 2. Roadmaps have different IDs and reflect authenticated user IDs
    roadmap_res_a = client.get("/api/roadmap", headers=headers_a)
    roadmap_res_b = client.get("/api/roadmap", headers=headers_b)

    assert roadmap_res_a.status_code == 200
    assert roadmap_res_b.status_code == 200

    data_a = roadmap_res_a.json()
    data_b = roadmap_res_b.json()

    assert data_a["id"] != data_b["id"]
    assert data_a["user_id"] == user_a_id
    assert data_b["user_id"] == user_b_id

    # 3 & 4. Tenant isolation: User Beta cannot access User Alpha's assessment attempt
    unauth_attempt = client.get(f"/api/assessments/{attempt_a_id}", headers=headers_b)
    assert unauth_attempt.status_code == 404

    # 5. Unknown module IDs return HTTP 404
    unknown_mod_res = client.get("/api/roadmap/mod_nonexistent_xyz", headers=headers_a)
    assert unknown_mod_res.status_code == 404


def test_progress_validation_and_payload_constraints(auth_client):
    """Phase 6: Strict status Literal and completion percentage validation (HTTP 422)."""
    client = auth_client

    # 1. Negative completion percentage rejected with HTTP 422
    neg_res = client.post("/api/roadmap/mod_py_types/complete", json={
        "completion_percentage": -15.0
    })
    assert neg_res.status_code == 422

    # 2. Percentage above 100 rejected with HTTP 422
    over_res = client.post("/api/roadmap/mod_py_types/complete", json={
        "completion_percentage": 125.0
    })
    assert over_res.status_code == 422

    # 3. Invalid status value rejected with HTTP 422 (strict Literal enforcement)
    invalid_status_res = client.post("/api/roadmap/mod_py_types/complete", json={
        "status": "flying"
    })
    assert invalid_status_res.status_code == 422

    # 4. Service-level validate_module_completion checks
    modules = [
        {"id": "mod_a", "prerequisite_module_ids": []},
        {"id": "mod_b", "prerequisite_module_ids": ["mod_a"]}
    ]
    # mod_b cannot be completed when mod_a is not completed
    with pytest.raises(ValueError, match="Cannot complete module 'mod_b'. Unmet prerequisites"):
        validate_module_completion("mod_b", modules, completed_module_ids=set())

    # mod_nonexistent raises ValueError
    with pytest.raises(ValueError, match="Module 'mod_nonexistent' not found in roadmap"):
        validate_module_completion("mod_nonexistent", modules, completed_module_ids=set())

    # mod_b succeeds when mod_a is completed
    assert validate_module_completion("mod_b", modules, completed_module_ids={"mod_a"}) is True


# ===========================================================================
# Phase 3A: Persistence & State Management Tests
# ===========================================================================

def test_persistence_workflow_and_idempotency(auth_client):
    """
    Tests:
    1. Completion persists after POST /complete
    2. Repeated completion is idempotent
    3. Original completion timestamp is preserved
    4. GET roadmap reflects stored progress and updates module lock state
    """
    client = auth_client

    # Verify initial state: mod_py_types is unlocked, mod_py_collections is locked
    init_res = client.get("/api/roadmap")
    assert init_res.status_code == 200
    init_data = init_res.json()
    types_mod = next(m for m in init_data["modules"] if m["id"] == "mod_py_types")
    col_mod = next(m for m in init_data["modules"] if m["id"] == "mod_py_collections")
    assert types_mod["status"] == "unlocked"
    assert col_mod["status"] == "locked"
    assert init_data["overall_progress_percentage"] == 0.0

    # 1. Complete mod_py_types
    complete_res1 = client.post("/api/roadmap/mod_py_types/complete")
    assert complete_res1.status_code == 200
    comp1 = complete_res1.json()
    assert comp1["module_id"] == "mod_py_types"
    assert comp1["status"] == "completed"
    assert comp1["completion_percentage"] == 100.0
    ts1 = comp1["updated_at"]
    assert ts1 is not None

    # 2. Repeated completion is idempotent and preserves original timestamp
    complete_res2 = client.post("/api/roadmap/mod_py_types/complete")
    assert complete_res2.status_code == 200
    comp2 = complete_res2.json()
    assert comp2["module_id"] == "mod_py_types"
    assert comp2["status"] == "completed"
    assert comp2["updated_at"] == ts1

    # 3. GET roadmap reflects progress: mod_py_types is completed, mod_py_collections is now unlocked
    after_res = client.get("/api/roadmap")
    assert after_res.status_code == 200
    after_data = after_res.json()
    types_after = next(m for m in after_data["modules"] if m["id"] == "mod_py_types")
    col_after = next(m for m in after_data["modules"] if m["id"] == "mod_py_collections")
    assert types_after["status"] == "completed"
    assert types_after["completion_percentage"] == 100.0
    assert col_after["status"] == "unlocked"
    assert after_data["overall_progress_percentage"] > 0.0


def test_prerequisite_gating_and_locked_module_rejection(auth_client):
    """
    Tests:
    5. Invalid module IDs are rejected (404)
    6. Locked modules cannot be completed (400)
    7. Completing prerequisites unlocks downstream modules
    """
    client = auth_client

    # 5. Invalid module ID
    bad_res = client.post("/api/roadmap/mod_invalid_ghost_module/complete")
    assert bad_res.status_code == 404

    # 6. Locked module without prerequisite: mod_py_functions requires mod_py_collections
    locked_res = client.post("/api/roadmap/mod_py_functions/complete")
    assert locked_res.status_code == 400
    assert "Unmet prerequisites" in locked_res.json()["detail"] or "prerequisite" in locked_res.json()["detail"].lower()

    # mod_py_collections requires mod_py_types
    col_locked_res = client.post("/api/roadmap/mod_py_collections/complete")
    assert col_locked_res.status_code == 400

    # 7. Complete prerequisite mod_py_types, then mod_py_collections succeeds
    res_prereq = client.post("/api/roadmap/mod_py_types/complete")
    assert res_prereq.status_code == 200

    col_unlock_res = client.post("/api/roadmap/mod_py_collections/complete")
    assert col_unlock_res.status_code == 200
    assert col_unlock_res.json()["status"] == "completed"


def test_tenant_isolation_progress():
    """
    4. User A cannot access or affect User B's progress.
    """
    client = TestClient(app)
    sfx_a = uuid.uuid4().hex[:6]
    sfx_b = uuid.uuid4().hex[:6]

    # Register User A
    res_a = client.post("/api/auth/register", json={
        "name": "User Alpha Progress",
        "email": f"alpha_prog_{sfx_a}@pragyax.test",
        "password": "PasswordAlpha123!"
    })
    token_a = res_a.json()["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B
    res_b = client.post("/api/auth/register", json={
        "name": "User Beta Progress",
        "email": f"beta_prog_{sfx_b}@pragyax.test",
        "password": "PasswordBeta123!"
    })
    token_b = res_b.json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A completes mod_py_types
    comp_a = client.post("/api/roadmap/mod_py_types/complete", headers=headers_a)
    assert comp_a.status_code == 200

    # User A roadmap shows mod_py_types completed
    rdm_a = client.get("/api/roadmap", headers=headers_a).json()
    types_a = next(m for m in rdm_a["modules"] if m["id"] == "mod_py_types")
    assert types_a["status"] == "completed"

    # User B roadmap must NOT show completed; mod_py_types must still be unlocked with 0% progress
    rdm_b = client.get("/api/roadmap", headers=headers_b).json()
    types_b = next(m for m in rdm_b["modules"] if m["id"] == "mod_py_types")
    assert types_b["status"] == "unlocked"
    assert types_b["completion_percentage"] == 0.0
    assert rdm_b["overall_progress_percentage"] == 0.0


def test_progress_persists_across_sessions_and_reassessment():
    """
    9. Progress survives new authentication sessions (logout / re-login)
    10. Reassessment does not erase module completion
    """
    client = TestClient(app)
    sfx = uuid.uuid4().hex[:6]
    email = f"session_test_{sfx}@pragyax.test"
    password = "SecurePassword123!"

    # 1. Register & complete mod_py_types
    reg_res = client.post("/api/auth/register", json={
        "name": "Session Learner",
        "email": email,
        "password": password
    })
    token1 = reg_res.json()["token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    comp_res = client.post("/api/roadmap/mod_py_types/complete", headers=headers1)
    assert comp_res.status_code == 200

    # 2. Login in a new session (different token)
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200
    token2 = login_res.json()["token"]
    assert token2 != token1
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Verify progress persists in new session
    rdm_new_session = client.get("/api/roadmap", headers=headers2).json()
    mod_types = next(m for m in rdm_new_session["modules"] if m["id"] == "mod_py_types")
    assert mod_types["status"] == "completed"
    assert mod_types["completion_percentage"] == 100.0

    # 3. Take assessment (submit answers)
    sub_res = client.post("/api/assessments/submit", json={
        "subject_id": "subj_python",
        "answers": {
            "q_py_1": "B",
            "q_py_2": "B",  # wrong
            "q_py_3": "C",
            "q_py_4": "B",
            "q_py_5": "A"
        }
    }, headers=headers2)
    assert sub_res.status_code == 200

    # Verify that roadmap after assessment still remembers mod_py_types as completed
    rdm_after_assess = client.get("/api/roadmap", headers=headers2).json()
    mod_types_after = next(m for m in rdm_after_assess["modules"] if m["id"] == "mod_py_types")
    assert mod_types_after["status"] == "completed"
    assert mod_types_after["completion_percentage"] == 100.0


def test_persistence_hardening_and_integrity(auth_client, monkeypatch):
    """
    Step 4 Hardening:
    - Successful completion persistence and record retrieval
    - Duplicate completion idempotency
    - Original completion timestamp preservation across calls
    - Missing saved row after attempted insert raises RuntimeError (no false success)
    """
    from backend.app.database.repository import Repository
    client = auth_client

    # 1. Complete mod_py_types via Repository directly
    reg_user_res = client.get("/api/roadmap")
    user_id = reg_user_res.json()["user_id"]

    rec1 = Repository.save_module_completion(user_id, "subj_python", "mod_py_types")
    assert rec1["user_id"] == user_id
    assert rec1["subject_id"] == "subj_python"
    assert rec1["module_id"] == "mod_py_types"
    assert rec1["status"] == "completed"
    assert rec1["completed_at"] is not None

    # 2. Duplicate completion preserves original timestamp and returns existing record
    rec2 = Repository.save_module_completion(user_id, "subj_python", "mod_py_types")
    assert rec2["id"] == rec1["id"]
    assert rec2["completed_at"] == rec1["completed_at"]

    # 3. Simulate database anomaly where SELECT returns None after insert -> must raise RuntimeError
    # (prevents returning fabricated completion records or false success)
    from backend.app.database import repository as repo_module
    from contextlib import contextmanager

    real_get_db = repo_module.get_db

    class BrokenCursor:
        def __init__(self, raw_cur):
            self._raw = raw_cur

        def execute(self, query, params=None):
            return self._raw.execute(query, params) if params is not None else self._raw.execute(query)

        def fetchone(self):
            return None  # Simulate missing row

        def fetchall(self):
            return []

    class BrokenConn:
        def __init__(self, raw_conn):
            self._conn = raw_conn

        def cursor(self):
            return BrokenCursor(self._conn.cursor())

        def commit(self):
            return self._conn.commit()

        def rollback(self):
            return self._conn.rollback()

        def close(self):
            return self._conn.close()

    @contextmanager
    def mock_broken_get_db():
        with real_get_db() as conn:
            yield BrokenConn(conn)

    monkeypatch.setattr(repo_module, "get_db", mock_broken_get_db)

    with pytest.raises(RuntimeError, match="Persistence failure: completion record for module"):
        Repository.save_module_completion(user_id, "subj_python", "mod_py_collections")
