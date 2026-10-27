"""
Authentication Router
Owned by: Arsh (FastAPI Backend Architecture)
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from ..schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserProfileResponse
from ..services.auth_service import (
    validate_email,
    generate_salt,
    hash_password,
    verify_password,
    generate_session_token,
    get_current_user,
    is_admin_user,
)
from ..services.referral_service import ReferralService
import time
from collections import defaultdict, deque

from ..database.repository import Repository

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Failed-login throttle: max 8 failures per email per 10 minutes.
# ponytail: in-process only; use a shared store (Redis/DB) when running more than one API worker.
_FAILS: dict = defaultdict(deque)
_MAX_FAILS, _WINDOW_S = 8, 600


def _check_throttle(key: str) -> None:
    q = _FAILS[key]
    now = time.monotonic()
    while q and now - q[0] > _WINDOW_S:
        q.popleft()
    if len(q) >= _MAX_FAILS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many failed attempts. Please wait a few minutes and try again.")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    """Registers a new learner account with salted PBKDF2 password hashing."""
    if not validate_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid email address."
        )

    if len(payload.name.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide your name (at least 2 characters)."
        )

    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    existing = Repository.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please log in."
        )

    salt = generate_salt()
    pwd_hash = hash_password(payload.password, salt)
    user = Repository.create_user(
        name=payload.name.strip(),
        email=payload.email.strip(),
        password_hash=pwd_hash,
        salt=salt
    )

    token = generate_session_token()
    Repository.create_session(user["id"], token)

    referral_notice = None
    if payload.referral_code and payload.referral_code.strip():
        applied = ReferralService.apply_referral_code(user["id"], payload.referral_code)
        referral_notice = applied.get("error") or applied.get("message")  # a bad code never blocks signup

    return {
        "token": token,
        "token_type": "Bearer",
        "user": {**user, "is_admin": is_admin_user(user)},
        "demo_notice": "Demo authentication active. Token valid for local session.",
        "referral_notice": referral_notice,
    }


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    """Authenticates learner and establishes session."""
    throttle_key = payload.email.strip().lower()
    _check_throttle(throttle_key)
    user = Repository.get_user_by_email(payload.email)
    if not user:
        _FAILS[throttle_key].append(time.monotonic())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(payload.password, user["password_hash"], user["salt"]):
        _FAILS[throttle_key].append(time.monotonic())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    _FAILS.pop(throttle_key, None)
    token = generate_session_token()
    Repository.create_session(user["id"], token)

    return {
        "token": token,
        "token_type": "Bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "created_at": user.get("created_at"),
            "is_admin": is_admin_user(user),
        },
        "demo_notice": "Demo authentication active. Token valid for local session."
    }


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(user: dict = Depends(get_current_user)):
    """Fetches currently authenticated learner profile."""
    return {**user, "is_admin": is_admin_user(user)}


@router.post("/logout")
def logout(user: dict = Depends(get_current_user), authorization: str = Header(None)):
    """Logs out user and invalidates current session token server-side."""
    Repository.delete_session(authorization.split(" ", 1)[1])
    return {"message": "Logged out successfully"}


from pydantic import BaseModel, Field
from ..database.connection import get_db, atomic_write


class UpdateProfile(BaseModel):
    name: str = Field(min_length=2,max_length=100)


@router.patch("/profile",response_model=UserProfileResponse)
@atomic_write
def update_profile(payload:UpdateProfile,user:dict=Depends(get_current_user)):
    name=payload.name.strip()
    if len(name)<2:raise HTTPException(400,"Display name must contain at least two characters")
    with get_db() as conn:
        conn.cursor().execute("UPDATE users SET name=? WHERE id=?",(name,user["id"]))
    return {**Repository.get_user_by_id(user["id"]),"is_admin":is_admin_user(user)}
