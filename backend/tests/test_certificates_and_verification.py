"""
Test Certificates and Shareable Achievements (Section F)
Validates certificate eligibility, issuance, cryptographic tamper-evident checks,
public verification endpoint, downloadable certificate view, and shareable achievement card data.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.connection import init_db
from backend.app.services.certificate_service import CertificateService
from backend.app.database.competition_repository import CompetitionRepository

client = TestClient(app)


def setup_module():
    init_db()


@pytest.fixture(autouse=True)
def certificate_users():
    from backend.app.database.connection import get_db
    with get_db() as conn:
        cur=conn.cursor()
        for uid in ['usr_cert_test_01','usr_tamper_test','usr_forger']:
            cur.execute("INSERT INTO users(id,name,email,password_hash,salt) VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
                        (uid,uid,uid+'@pragyax.test','unused-test-hash','unused-test-salt'))


def test_certificate_issuance_and_public_verification():
    # Issue a valid verified certificate
    cert = CertificateService.issue_certificate(
        user_id="usr_cert_test_01",
        user_name="Ananya Verma",
        cert_type="ASSESSMENT",
        title="Python Data Structures & Algorithms Mastery",
        description="Demonstrated top-tier mastery in algorithmic problem solving",
        metadata={"score": 5, "total": 5, "percentage": 100.0}
    )

    verif_id = cert["verification_id"]
    assert verif_id.startswith("PRAGYA-CERT-")

    # 1. Authoritative public verification
    verif_res = client.get(f"/api/certificates/verify/{verif_id}")
    assert verif_res.status_code == 200
    data = verif_res.json()
    assert data["is_valid"] is True
    assert data["recipient_name"] == "Ananya Verma"
    assert data["title"] == "Python Data Structures & Algorithms Mastery"
    assert "verification_hash" in data

    # 2. Non-existent verification ID returns 404
    bad_res = client.get("/api/certificates/verify/PRAGYA-CERT-2026-NONEXISTENT")
    assert bad_res.status_code == 404

    # 3. Shareable social card metadata
    share_res = client.get(f"/api/certificates/{verif_id}/share")
    assert share_res.status_code == 200
    card = share_res.json()
    assert card["recipient"] == "Ananya Verma"
    assert "verification_url" in card
    assert "share_text" in card

    # 4. Downloadable certificate HTML
    dl_res = client.get(f"/api/certificates/{verif_id}/download")
    assert dl_res.status_code == 200
    assert "text/html" in dl_res.headers["content-type"]
    assert "Ananya Verma" in dl_res.text
    assert verif_id in dl_res.text


def test_tamper_evident_cryptographic_verification():
    # Issue legitimate certificate
    cert = CertificateService.issue_certificate(
        user_id="usr_tamper_test",
        user_name="Honest Student",
        cert_type="BATTLE_WINNER",
        title="1v1 Battle Grandmaster",
        description="Consecutive duel victory",
        metadata={"wins": 10}
    )
    verif_id = cert["verification_id"]

    # Tamper with the database row directly (e.g. modify verification_hash)
    from backend.app.database.connection import get_db
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE certificates SET verification_hash = 'TAMPERED_HASH_123' WHERE verification_id = ?;", (verif_id,))

    # Verification must reject tampered record
    tamper_check = client.get(f"/api/certificates/verify/{verif_id}")
    assert tamper_check.status_code == 404
    assert "tamper" in tamper_check.json()["detail"].lower()


def test_forged_certificate_rejected():
    """Verify that crafting a forged certificate without the server's SECRET_KEY is rejected."""
    import json
    import uuid
    from backend.app.database.connection import get_db

    forged_verif_id = f"PRAGYA-CERT-2026-FORGED{uuid.uuid4().hex[:4].upper()}"
    # Attacker attempts to forge with a fake signature or wrong key
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO certificates (
                id, verification_id, user_id, user_name, cert_type, title, description, metadata_json, verification_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            f"cert_forged_{uuid.uuid4().hex[:6]}",
            forged_verif_id,
            "usr_forger",
            "Malicious Forger",
            "COMPETITION_WINNER",
            "Forged Championship",
            "Fraudulent certificate",
            json.dumps({"forged": True}),
            "f" * 64  # Invalid HMAC signature
        ))

    check = client.get(f"/api/certificates/verify/{forged_verif_id}")
    assert check.status_code == 404
    assert "tamper" in check.json()["detail"].lower()
