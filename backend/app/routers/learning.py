"""
Learning chats API: independent per-subject chats with their own history, diagnostic, roadmap, lessons,
practice, revision. Plus curated projects and the skill profile. Every route is scoped to the authenticated user.
"""

from typing import Dict, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..services import curriculum
from ..services.auth_service import get_current_user
from ..services.learning_service import LearningService

router = APIRouter(prefix="/learn", tags=["Learning"])


class CreateChatRequest(BaseModel):
    subject_id: Optional[str] = None          # one of the curated subject ids
    custom_subject: Optional[str] = Field(None, max_length=80)  # any other subject (mentor-only)
    title: Optional[str] = Field(None, max_length=80)


class PatchChatRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=80)
    archived: Optional[bool] = None


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    mode: str = "explain"


class AssessmentRequest(BaseModel):
    answers: Dict[str, str]


class PracticeRequest(BaseModel):
    answers: Dict[str, int]


class MilestoneRequest(BaseModel):
    index: int
    done: bool = True


class ProjectSubmitRequest(BaseModel):
    text: str = Field("", max_length=4000)
    url: Optional[str] = Field(None, max_length=500)
    rubric_scores: Dict[str, int]


@router.get("/catalog")
def catalog(user: dict = Depends(get_current_user)):
    """Curated subjects (the only ones with diagnostics/roadmaps) and the modes the mentor supports."""
    return {
        "subjects": [{"id": sid, "title": t, "modules": len(curriculum.subject_modules(sid))}
                     for sid, t in curriculum.SUBJECT_TITLES.items()],
        "custom_subjects_note": "Any other subject works as a mentor-only chat with no validated curriculum.",
    }


@router.post("/chats", status_code=201)
def create_chat(payload: CreateChatRequest, user: dict = Depends(get_current_user)):
    return LearningService.create_chat(user, payload.subject_id, payload.custom_subject, payload.title)


@router.get("/chats")
def list_chats(include_archived: bool = False, user: dict = Depends(get_current_user)):
    return {"chats": LearningService.list_chats(user, include_archived)}


@router.get("/chats/{chat_id}")
def get_chat(chat_id: str, user: dict = Depends(get_current_user)):
    return LearningService.chat_state(LearningService.get_owned_chat(user, chat_id), user)


@router.patch("/chats/{chat_id}")
def patch_chat(chat_id: str, payload: PatchChatRequest, user: dict = Depends(get_current_user)):
    from ..database.learning_repository import LearningRepository
    chat = LearningService.get_owned_chat(user, chat_id)
    LearningRepository.update_chat(
        chat["id"], user["id"], title=payload.title.strip() if payload.title else None,
        status=None if payload.archived is None else ("archived" if payload.archived else "active"))
    return LearningService.chat_state(LearningService.get_owned_chat(user, chat_id), user)


@router.get("/chats/{chat_id}/messages")
def get_messages(chat_id: str, user: dict = Depends(get_current_user)):
    from ..database.learning_repository import LearningRepository
    chat = LearningService.get_owned_chat(user, chat_id)
    return {"messages": LearningRepository.get_messages(chat["id"], 100)}


@router.post("/chats/{chat_id}/messages")
def post_message(chat_id: str, payload: MessageRequest, user: dict = Depends(get_current_user)):
    return LearningService.post_message(user, LearningService.get_owned_chat(user, chat_id), payload.message, payload.mode)


@router.get("/chats/{chat_id}/assessment")
def assessment_questions(chat_id: str, user: dict = Depends(get_current_user)):
    """Questions only: answer keys and explanations are never sent before submission."""
    chat = LearningService.get_owned_chat(user, chat_id)
    return {"questions": LearningService.assessment_questions(chat)}


@router.post("/chats/{chat_id}/assessment")
def submit_assessment(chat_id: str, payload: AssessmentRequest, user: dict = Depends(get_current_user)):
    return LearningService.submit_assessment(user, LearningService.get_owned_chat(user, chat_id), payload.answers)


@router.get("/chats/{chat_id}/modules/{module_id}")
def get_module(chat_id: str, module_id: str, user: dict = Depends(get_current_user)):
    return LearningService.get_module(user, LearningService.get_owned_chat(user, chat_id), module_id)


@router.post("/chats/{chat_id}/modules/{module_id}/practice")
def submit_practice(chat_id: str, module_id: str, payload: PracticeRequest, user: dict = Depends(get_current_user)):
    return LearningService.submit_practice(user, LearningService.get_owned_chat(user, chat_id), module_id, payload.answers)


@router.get("/chats/{chat_id}/revision")
def revision(chat_id: str, user: dict = Depends(get_current_user)):
    return LearningService.revision(user, LearningService.get_owned_chat(user, chat_id))


@router.get("/projects")
def list_projects(user: dict = Depends(get_current_user)):
    return {"projects": LearningService.list_projects(user)}


@router.post("/projects/{project_id}/milestones")
def milestone(project_id: str, payload: MilestoneRequest, user: dict = Depends(get_current_user)):
    return LearningService.toggle_milestone(user, project_id, payload.index, payload.done)


@router.post("/projects/{project_id}/submit")
def submit_project(project_id: str, payload: ProjectSubmitRequest, user: dict = Depends(get_current_user)):
    return LearningService.submit_project(user, project_id, payload.text, payload.url, payload.rubric_scores)


@router.get("/skill-profile")
def skill_profile(user: dict = Depends(get_current_user)):
    return LearningService.skill_profile(user)
