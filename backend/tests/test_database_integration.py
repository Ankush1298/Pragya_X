"""
Targeted Database Connection and Compatibility Test Suite
Tests:
1. PostgreSQL connection configuration validation & sanitization
2. Database connection failure handling (strictly no silent fallback)
3. Missing PostgreSQL configuration fails clearly
4. Repository SQL compatibility (ON CONFLICT, portable ordering, booleans)
5. Connection pool cleanup
6. Read-only SELECT 1 ping_db() check
"""

import os
import tempfile
import pytest
from backend.app.config import settings, validate_postgres_url, sanitize_db_url
from backend.app.database.connection import (
    get_db,
    ping_db,
    init_db,
    close_db_pool,
    DatabaseConnectionError,
    PostgresCursorWrapper
)
from backend.app.database.repository import Repository




def test_postgres_url_validation_and_sanitization():
    # Valid PostgreSQL URL
    valid_url = "postgresql://myuser:supersecret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
    normalized = validate_postgres_url(valid_url)
    assert normalized.startswith("postgresql://")

    # Normalized legacy postgres:// prefix
    legacy_url = "postgres://myuser:supersecret@db.supabase.co:5432/postgres"
    assert validate_postgres_url(legacy_url).startswith("postgresql://")

    # Invalid scheme rejection
    with pytest.raises(ValueError, match="DATABASE_URL must start with"):
        validate_postgres_url("mysql://user:pass@localhost/db")

    # Sanitization hides passwords
    sanitized = sanitize_db_url(valid_url)
    assert "supersecret" not in sanitized
    assert ":***@" in sanitized
    assert "aws-0-ap-south-1.pooler.supabase.com:6543" in sanitized


def test_missing_database_url_fails(monkeypatch):
    close_db_pool()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConnectionError, match="DATABASE_URL"):
        init_db()
    assert ping_db()["connected"] is False


def test_postgres_fail_fast_without_fallback(monkeypatch):
    """
    CRITICAL REQUIREMENT:
    If DATABASE_URL is configured but unreachable, the system must FAIL FAST
    with DatabaseConnectionError and NEVER switch database engines.
    """
    close_db_pool()
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://fake_user:fake_pass@127.0.0.1:59999/nonexistent?sslmode=disable")
    assert settings.is_postgres is True

    with pytest.raises(DatabaseConnectionError):
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")


def test_cursor_placeholder_translation():
    class DummyCursor:
        def __init__(self):
            self.last_query = None
            self.last_params = None

        def execute(self, query, params=None):
            self.last_query = query
            self.last_params = params
            return self

    dummy = DummyCursor()
    wrapper = PostgresCursorWrapper(dummy)
    wrapper.execute("SELECT * FROM users WHERE email = ? AND id = ?;", ("test@example.com", "usr_123"))
    
    assert dummy.last_query == "SELECT * FROM users WHERE email = %s AND id = %s;"
    assert dummy.last_params == ("test@example.com", "usr_123")


def test_repository_portable_operations():
    # 1. Create User
    user = Repository.create_user("Test User", "test_portable@pragyax.test", "hash123", "salt123")
    assert user["email"] == "test_portable@pragyax.test"

    # 2. Session with ON CONFLICT DO UPDATE
    token = "pragya_test_portable_token"
    Repository.create_session(user["id"], token)
    # Upsert same token should succeed without duplicate key error
    Repository.create_session(user["id"], token)
    
    fetched_user = Repository.get_user_by_token(token)
    assert fetched_user is not None
    assert fetched_user["id"] == user["id"]

    # 3. Chat history without rowid
    msg = Repository.save_chat_message(user["id"], "Python", "user", "What is LEGB?", ["Followup 1"])
    assert msg["id"].startswith("msg_")
    history = Repository.get_chat_history(user["id"], limit=10)
    assert len(history) >= 1
    assert history[-1]["content"] == "What is LEGB?"

    # 4. Badge awarding with ON CONFLICT DO NOTHING
    # Submitting challenge creates submission and awards badge
    chal = Repository.get_daily_challenge(user["id"])
    assert chal["id"] == "chal_today_py"
    
    result = Repository.submit_daily_challenge(user["id"], chal["id"], "B")
    assert result["is_correct"] is True
    assert result["points_awarded"] == 50

    badges = Repository.get_user_badges(user["id"])
    assert any(b["badge_key"] == "daily_striker" for b in badges)


def test_connection_cleanup():
    close_db_pool()
    from backend.app.database.connection import _pool
    assert _pool is None
