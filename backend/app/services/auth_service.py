"""
Authentication and Session Security Service
Owned by: Arsh (FastAPI Backend Architecture)
Implements PBKDF2-HMAC-SHA256 password hashing with unique random salt,
constant-time verification, and local token session management.
"""

import hashlib
import hmac
import os
import secrets
import re
from fastapi import Header, HTTPException, status
from ..config import settings
from ..database.repository import Repository


def validate_email(email: str) -> bool:
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(email_regex, email.strip()))


def generate_salt() -> str:
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100_000
    )
    return key.hex()


def verify_password(plain_password: str, stored_hash: str, salt: str) -> bool:
    new_hash = hash_password(plain_password, salt)
    return hmac.compare_digest(new_hash, stored_hash)


def generate_session_token() -> str:
    return f"pragya_{secrets.token_urlsafe(32)}"


def get_current_user(authorization: str = Header(None)) -> dict:
    """
    FastAPI Dependency to enforce authentication.
    Requires header: 'Authorization: Bearer <token>'
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Please log in to proceed.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization scheme. Use 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    user = Repository.get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def is_admin_user(user: dict) -> bool:
    """Server-side admin check: email must be in the ADMIN_EMAILS allow-list (empty by default)."""
    return (user.get("email") or "").lower() in settings.ADMIN_EMAILS
