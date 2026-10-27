"""
Hosted Competitions Router (College & Company Challenges)
Owned by: Ankush (Gamification & Competition Module Owner)
Handles organization registration, challenge scheduling, server-authoritative grading,
rankings, winner announcements, and organizer dashboards.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from ..services.auth_service import get_current_user, is_admin_user
from ..services.hosted_competition_service import HostedCompetitionService
from ..schemas.competitions import (
    OrganizationCreateRequest,
    OrganizationResponse,
    CompetitionCreateRequest,
    CompetitionSubmitRequest,
    CompetitionLeaderboardEntry
)

router = APIRouter(prefix="/competitions", tags=["Hosted Competitions"])


@router.post("/organizations")
def register_organization(payload: OrganizationCreateRequest, user: dict = Depends(get_current_user)):
    """Registers a new organization for hosting student, college, or company challenges."""
    result = HostedCompetitionService.register_organization(
        name=payload.name,
        org_type=payload.org_type,
        domain=payload.domain,
        description=payload.description,
        created_by_user_id=user["id"]
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


@router.get("/organizations")
def list_organizations(verified_only: bool = False):
    """Lists host organizations."""
    return HostedCompetitionService.list_organizations(verified_only=verified_only)


@router.post("/create")
def create_competition(payload: CompetitionCreateRequest, user: dict = Depends(get_current_user)):
    """
    Creates and schedules a hosted challenge.
    Enforces verified host status: College and Company challenges require admin verification.
    """
    is_admin = is_admin_user(user)
    result = HostedCompetitionService.create_competition(
        user_id=user["id"],
        org_id=payload.org_id,
        title=payload.title,
        description=payload.description,
        subject_id=payload.subject_id,
        difficulty=payload.difficulty,
        start_time=payload.start_time,
        end_time=payload.end_time,
        questions=[q.model_dump() for q in payload.questions],
        eligibility_rules=payload.eligibility_rules,
        is_admin=is_admin
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


@router.get("/list")
def list_competitions(status_filter: Optional[str] = None, host_type: Optional[str] = None):
    """Lists hosted competitions, hiding answer keys from public views."""
    return HostedCompetitionService.list_competitions(status=status_filter, host_type=host_type)


@router.get("/{comp_id}")
def get_competition(comp_id: str, user: dict = Depends(get_current_user)):
    """Retrieves competition details for taking the challenge."""
    comp = HostedCompetitionService.get_competition_for_student(comp_id, user_id=user["id"])
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found.")
    return comp


@router.post("/{comp_id}/submit")
def submit_competition(comp_id: str, payload: CompetitionSubmitRequest, user: dict = Depends(get_current_user)):
    """
    Submits participant answers for a competition.
    Graded authoritatively on the server; awards XP and updates rankings.
    """
    result = HostedCompetitionService.submit_competition(
        comp_id=comp_id,
        user_id=user["id"],
        user_name=user["name"],
        answers=payload.answers,
        time_taken_seconds=payload.time_taken_seconds
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


@router.get("/{comp_id}/leaderboard")
def get_competition_leaderboard(comp_id: str):
    """Retrieves ranked competition leaderboard."""
    return HostedCompetitionService.get_competition_leaderboard(comp_id)


@router.get("/{comp_id}/dashboard")
def get_organizer_dashboard(comp_id: str, user: dict = Depends(get_current_user)):
    """Organizer result dashboard with analytics and participant standings."""
    is_admin = is_admin_user(user)
    result = HostedCompetitionService.get_organizer_dashboard(comp_id, user_id=user["id"], is_admin=is_admin)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result["error"])
    return result


@router.post("/{comp_id}/announce-winners")
def announce_winners(comp_id: str, user: dict = Depends(get_current_user)):
    """Announces winners and issues verified certificates to top performers."""
    is_admin = is_admin_user(user)
    result = HostedCompetitionService.announce_winners_and_issue_certificates(comp_id, user_id=user["id"], is_admin=is_admin)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result
