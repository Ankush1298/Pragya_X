"""
Assessment and AI Evaluation Router
Owned by: Ekansh (AI/ML) & Arsh (Backend)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import sys
import os

# Pluggable AI import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from ai.factory import get_ai_provider

from ..schemas.assessments import (
    AssessmentQuestionPublic,
    AssessmentSubmitRequest,
    AssessmentResultResponse,
    AssessmentHistoryResponse,
    AssessmentHistoryItem
)
from ..services.learning_service import run_assessment
from ..services.auth_service import get_current_user
from ..database.repository import Repository

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.get("/questions", response_model=List[AssessmentQuestionPublic])
def get_assessment_questions(subject_id: str = "subj_python", user: dict = Depends(get_current_user)):
    """
    Retrieves the 5 assessment questions.
    SECURITY: Correct answers and explanations are NEVER exposed prior to submission.
    """
    raw_questions = Repository.get_assessment_questions(subject_id)
    if not raw_questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No questions found for the selected subject."
        )

    # Convert to public schema
    return [
        AssessmentQuestionPublic(
            id=q["id"],
            subject_id=q["subject_id"],
            question_number=q["question_number"],
            question_text=q["question_text"],
            option_a=q["option_a"],
            option_b=q["option_b"],
            option_c=q["option_c"],
            option_d=q["option_d"],
            topic=q["topic"],
            difficulty=q["difficulty"]
        )
        for q in raw_questions
    ]


@router.post("/submit", response_model=AssessmentResultResponse)
def submit_assessment(payload: AssessmentSubmitRequest, user: dict = Depends(get_current_user)):
    """Evaluates a submission against server-side keys. Prefer POST /learn/chats/{id}/assessment for chat-scoped diagnostics."""
    return run_assessment(user, payload.subject_id, payload.answers, provider_factory=get_ai_provider)


@router.get("/history", response_model=AssessmentHistoryResponse)
def get_assessment_history(user: dict = Depends(get_current_user)):
    """Returns list of past completed assessment attempts for the authenticated user."""
    attempts = Repository.get_user_assessment_attempts(user["id"], limit=20)
    return {
        "attempts": [
            AssessmentHistoryItem(
                id=a["id"],
                subject_id=a["subject_id"],
                subject_title=a["subject_title"],
                score=a["score"],
                total=a["total"],
                percentage=a["percentage"],
                proficiency_level=a["proficiency_level"],
                created_at=a.get("created_at")
            )
            for a in attempts
        ]
    }


@router.get("/{attempt_id}", response_model=AssessmentResultResponse)
def get_assessment_attempt_details(attempt_id: str, user: dict = Depends(get_current_user)):
    """
    Retrieves full breakdown of a past assessment.
    Enforces user isolation: Attempt must belong to authenticated user.
    """
    attempt = Repository.get_assessment_attempt_by_id(attempt_id, user["id"])
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment attempt not found or unauthorized."
        )

    try:
        ai_provider = get_ai_provider()
        provider_name = ai_provider.provider_name
        is_mock = ai_provider.is_mock
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Provider metadata is temporarily unavailable."
        ) from None

    return {
        "id": attempt["id"],
        "user_id": user["id"],
        "subject_id": attempt["subject_id"],
        "subject_title": attempt.get("subject_title", "Python Programming"),
        "score": attempt["score"],
        "total": attempt["total"],
        "percentage": attempt["percentage"],
        "proficiency_level": attempt["proficiency_level"],
        "summary_feedback": attempt["summary_feedback"],
        "recommended_topics": attempt["recommended_topics"],
        "breakdown": attempt["breakdown"],
        "is_mock": is_mock,
        "provider": provider_name,
        "created_at": attempt.get("created_at")
    }
