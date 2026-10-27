"""Notification center: list, read/unread, preferences (opt-outs, quiet hours)."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..database.learning_repository import LearningRepository
from ..services.auth_service import get_current_user
from ..services.learning_service import LearningService
from ..services.notification_service import valid_hhmm

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class PrefsRequest(BaseModel):
    battles: bool = True
    achievements: bool = True
    reminders: bool = True
    projects: bool = True
    quiet_start: Optional[str] = None  # "HH:MM" 24h, server local time
    quiet_end: Optional[str] = None


@router.get("")
def list_notifications(user: dict = Depends(get_current_user)):
    LearningService.generate_revision_reminders(user["id"])
    return {"notifications": LearningRepository.list_notifications(user["id"]),
            "unread": LearningRepository.unread_count(user["id"])}


@router.get("/unread-count")
def unread_count(user: dict = Depends(get_current_user)):
    return {"unread": LearningRepository.unread_count(user["id"])}


@router.post("/read")
def mark_read(notification_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Mark one notification (or all when no id given) as read."""
    LearningRepository.mark_read(user["id"], notification_id)
    return {"unread": LearningRepository.unread_count(user["id"])}


@router.get("/preferences")
def get_preferences(user: dict = Depends(get_current_user)):
    p = LearningRepository.get_prefs(user["id"])
    return {k: (bool(p[k]) if k in ("battles", "achievements", "reminders", "projects") else p[k])
            for k in ("battles", "achievements", "reminders", "projects", "quiet_start", "quiet_end")}


@router.put("/preferences")
def put_preferences(payload: PrefsRequest, user: dict = Depends(get_current_user)):
    if not (valid_hhmm(payload.quiet_start) and valid_hhmm(payload.quiet_end)):
        raise HTTPException(status_code=400, detail="Quiet hours must be HH:MM (24-hour).")
    LearningRepository.save_prefs(user["id"], payload.model_dump())
    return get_preferences(user)
