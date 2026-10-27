"""
Challenge Management Router (Ankush's Module)
Provides daily gamified coding snippets, library browsing, topic/difficulty filtering,
streak tracking, server-authoritative submission grading, and leaderboards.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from ..schemas.challenges import (
    DailyChallengeResponse,
    ChallengeSubmitRequest,
    ChallengeResultResponse,
    ChallengeLibraryItem,
    UserStreakResponse,
    ChallengeCreateRequest
)
from ..services.auth_service import get_current_user, is_admin_user
from ..services.challenge_service import ChallengeService
from ..services.referral_service import ReferralService

router = APIRouter(prefix="/challenges", tags=["Challenge Management"])


@router.get("/daily", response_model=DailyChallengeResponse)
def get_daily_challenge(subject_id: str = "subj_python", date_str: Optional[str] = None, user: dict = Depends(get_current_user)):
    """
    Retrieves today's micro-challenge.
    Maintains V1 default compatibility while supporting deterministic date rotation.
    Masks the correct option until the student has submitted.
    """
    if date_str:
        chal = ChallengeService.get_daily_challenge_for_date(
            subject_id=subject_id,
            target_date=date_str,
            user_id=user["id"]
        )
    else:
        from ..database.repository import Repository
        chal = Repository.get_daily_challenge(user["id"])
        if not chal:
            chal = ChallengeService.get_daily_challenge_for_date(
                subject_id=subject_id,
                target_date=None,
                user_id=user["id"]
            )

    if not chal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No daily challenge active at this time."
        )
    return chal


@router.post("/submit", response_model=ChallengeResultResponse)
def submit_challenge(payload: ChallengeSubmitRequest, user: dict = Depends(get_current_user)):
    """
    Submits user answer for a challenge.
    Awards points and updates streaks exactly once per user.
    If student was invited via referral, completion unlocks referral rewards!
    """
    choice = payload.selected_option.strip().upper()
    if choice not in {"A", "B", "C", "D"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="selected_option must be A, B, C, or D."
        )

    from ..database.repository import Repository
    if payload.challenge_id.startswith("chal_today"):
        result = Repository.submit_daily_challenge(
            user_id=user["id"],
            challenge_id=payload.challenge_id,
            selected_option=choice
        )
        if result.get("is_correct"):
            from datetime import date
            from ..database.competition_repository import CompetitionRepository
            CompetitionRepository.update_user_streak(user["id"], date.today().isoformat())
    else:
        result = ChallengeService.submit_challenge(
            user_id=user["id"],
            challenge_id=payload.challenge_id,
            selected_option=choice
        )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    # Trigger qualifying referral reward check
    ReferralService.check_and_qualify_referral(user["id"], "daily_challenge")

    return result


@router.get("/library", response_model=List[ChallengeLibraryItem])
def get_challenge_library(topic: Optional[str] = None, difficulty: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Retrieves all active challenges, filtered by topic and difficulty, with completion flags."""
    return ChallengeService.get_challenge_library(
        topic=topic,
        difficulty=difficulty,
        user_id=user["id"]
    )


@router.get("/history")
def get_challenge_history(user: dict = Depends(get_current_user)):
    """Retrieves student's challenge submission history."""
    return ChallengeService.get_challenge_history(user["id"])


@router.get("/streak", response_model=UserStreakResponse)
def get_user_streak(user: dict = Depends(get_current_user)):
    """Returns current learning & challenge streak status."""
    return ChallengeService.get_user_streak(user["id"])


@router.get("/leaderboard")
def get_challenge_leaderboard(limit: int = 25):
    """Retrieves top performers ranked by challenge points."""
    return ChallengeService.get_challenge_leaderboard(limit=limit)


@router.post("/create")
def create_challenge(payload: ChallengeCreateRequest, user: dict = Depends(get_current_user)):
    """Creates a new platform or hosted challenge."""
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="Only administrators can publish platform challenges. Use a student-hosted competition for peer challenges.")
    from ..database.competition_repository import CompetitionRepository
    created = CompetitionRepository.create_challenge({
        "subject_id": payload.subject_id,
        "title": payload.title,
        "topic": payload.topic,
        "difficulty": payload.difficulty,
        "description": payload.description,
        "code_snippet": payload.code_snippet,
        "option_a": payload.option_a,
        "option_b": payload.option_b,
        "option_c": payload.option_c,
        "option_d": payload.option_d,
        "correct_option": payload.correct_option,
        "explanation": payload.explanation,
        "points": payload.points,
        "scheduled_date": payload.scheduled_date,
        "created_by": user["id"]
    })
    return created
