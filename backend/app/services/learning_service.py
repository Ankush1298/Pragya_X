from ..database.connection import atomic_write
"""
Learning engine: independent learning chats, diagnostics, per-chat roadmaps, lessons, practice, revision,
projects and the skill profile. Subject-agnostic: curated subjects share one data shape (services/curriculum.py);
any other subject is a mentor-only chat that is clearly labelled as having no validated curriculum.
Grading of objective questions is always deterministic and server-side.
"""

import logging
import sys
import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from ai.factory import get_ai_provider  # noqa: E402

from ..database.competition_repository import CompetitionRepository
from ..database.learning_repository import LearningRepository
from ..database.repository import Repository
from . import curriculum
from .assessment_service import evaluate_assessment
from .notification_service import notify
from .roadmap_service import build_deterministic_roadmap

logger = logging.getLogger(__name__)

MODULE_XP = 40
MODES = {"explain", "hint", "simpler", "hinglish", "socratic", "mistake"}
_MODE_INSTRUCTIONS = {
    "explain": "",
    "hint": "The learner wants a HINT only. Do NOT give the final answer; give one guiding hint and a question to try next.",
    "simpler": "Explain in simpler words with an everyday analogy, then check understanding with one easy question.",
    "hinglish": "Reply in Hinglish (Hindi written in Latin script mixed with simple English).",
    "socratic": "Teach Socratically: ask short guiding questions and reveal the answer only after the learner attempts it.",
    "mistake": "Analyse the learner's mistake: name the misconception, explain why it is wrong, show a corrected example.",
}
_MOCK_MODE_NOTE = {
    "hint": "Hint mode needs a live AI mentor to tailor hints. Offline Demo AI shows the closest concept note instead; try the problem yourself first.",
    "hinglish": "Hinglish replies need a live AI provider. The offline Demo AI answers in English.",
    "simpler": "Simplified explanations need a live AI provider. Showing the standard concept note.",
    "socratic": "Socratic tutoring needs a live AI provider. Showing the standard concept note.",
    "mistake": "Mistake analysis needs a live AI provider. See the Revision tab for explanations of the questions you missed.",
}


def _err(code: int, msg: str):
    raise HTTPException(status_code=code, detail=msg)


class LearningService:
    # ------------------------------------------------------------------ chats
    @staticmethod
    def create_chat(user: dict, subject_id: Optional[str], custom_subject: Optional[str], title: Optional[str]) -> Dict[str, Any]:
        if subject_id:
            if not curriculum.is_curated(subject_id):
                _err(400, "Unknown curated subject. Use custom_subject for any other topic.")
            subject_title = curriculum.SUBJECT_TITLES[subject_id]
        else:
            subject_title = (custom_subject or "").strip()
            if len(subject_title) < 2:
                _err(400, "Choose a curated subject or enter a subject name.")
            subject_title = subject_title[:80]
        chat = LearningRepository.create_chat(user["id"], subject_id, subject_title, (title or subject_title).strip()[:80] or subject_title)
        return LearningService.chat_state(chat, user)

    @staticmethod
    def get_owned_chat(user: dict, chat_id: str) -> Dict[str, Any]:
        chat = LearningRepository.get_chat(chat_id, user["id"])
        if not chat:  # same answer for "missing" and "someone else's": no existence leak
            _err(404, "Learning chat not found.")
        return chat

    @staticmethod
    def list_chats(user: dict, include_archived: bool = False) -> List[Dict[str, Any]]:
        out = []
        for chat in LearningRepository.list_chats(user["id"], include_archived):
            st = LearningService.chat_state(chat, user, light=True)
            out.append(st)
        return out

    # ------------------------------------------------------------------ state
    @staticmethod
    def _weak_strong(attempt: Optional[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
        if not attempt:
            return [], []
        weak, strong = [], []
        for b in attempt.get("breakdown", []):
            (strong if b.get("is_correct") else weak).append(b.get("topic", ""))
        return [w for w in weak if w], [s for s in strong if s]

    @staticmethod
    def _roadmap(chat: Dict[str, Any], weaknesses: List[str], completed: List[str]) -> Optional[Dict[str, Any]]:
        sid = chat["subject_id"]
        if not curriculum.is_curated(sid):
            return None
        # keep completed modules in the path even if a later reassessment no longer flags them
        extra = []
        for mid in completed:
            m = curriculum.get_module(mid)
            if m:
                extra.append(max(m["catalog"]["keywords"], key=len))
        road = build_deterministic_roadmap(sid, weaknesses + extra, user_id=chat["id"], completed_module_ids=set(completed))
        return road

    @staticmethod
    def chat_state(chat: Dict[str, Any], user: dict, light: bool = False) -> Dict[str, Any]:
        cid = chat["id"]
        attempts = LearningRepository.chat_attempts(cid)
        first = attempts[0] if attempts else None
        latest = attempts[-1] if attempts else None
        weak, strong = LearningService._weak_strong(latest)
        curated = curriculum.is_curated(chat["subject_id"])
        completed = LearningRepository.completed_module_ids(cid)
        progress = LearningRepository.progress_map(cid)
        roadmap = LearningService._roadmap(chat, weak, completed) if (curated and latest) else None

        modules: List[Dict[str, Any]] = []
        current = None
        if roadmap:
            for m in roadmap["modules"]:
                p = progress.get(m["id"], {})
                total_q = p.get("total_questions") or 0
                mastery = round(100 * p.get("best_correct", 0) / total_q) if total_q else None
                item = {**m, "lesson_viewed": bool(p.get("lesson_viewed")), "mastery_percentage": mastery,
                        "practice_best": f"{p.get('best_correct', 0)}/{total_q}" if total_q else None,
                        "status": "completed" if m["id"] in completed else m["status"]}
                modules.append(item)
            current = next((m for m in modules if m["status"] == "unlocked"), None)
            done = sum(1 for m in modules if m["status"] == "completed")
            overall = round(100 * done / len(modules), 1) if modules else 0.0
        else:
            overall = 0.0

        mistakes = LearningRepository.mistakes(cid, 50) if not light else []
        state: Dict[str, Any] = {
            "id": cid, "title": chat["title"], "subject_id": chat["subject_id"], "subject_title": chat["subject_title"],
            "status": chat["status"], "curated": curated, "created_at": chat.get("created_at"),
            "updated_at": chat.get("updated_at"),
            "has_diagnostic": bool(latest),
            "latest_score": {"score": latest["score"], "total": latest["total"], "percentage": latest["percentage"],
                             "level": latest["proficiency_level"]} if latest else None,
            "overall_progress": overall,
            "modules_total": len(modules), "modules_completed": sum(1 for m in modules if m["status"] == "completed"),
            "current_module_title": current["title"] if current else None,
        }
        if light:
            return state

        state.update({
            "limitation": None if curated else (
                "No validated PragyaX curriculum exists for this subject. The mentor answers using the configured AI "
                "provider only; there is no diagnostic, roadmap or graded practice, and offline Demo AI cannot discuss it."),
            "weaknesses": sorted(set(weak), key=weak.index), "strengths": sorted(set(strong), key=strong.index),
            "level_note": ("Estimated from a short 5-question diagnostic. This is an indication, not an accredited skill test."
                           if latest else None),
            "roadmap": {**roadmap, "modules": modules, "overall_progress_percentage": overall} if roadmap else None,
            "current_module": current,
            "assessment_history": [{"id": a["id"], "kind": a["kind"], "score": a["score"], "total": a["total"],
                                    "percentage": a["percentage"], "level": a["proficiency_level"],
                                    "created_at": a["created_at"]} for a in attempts],
            "improvement": ({"first_percentage": first["percentage"], "latest_percentage": latest["percentage"],
                             "delta": round(latest["percentage"] - first["percentage"], 1)}
                            if first and latest and first["id"] != latest["id"] else None),
            "unresolved_mistakes": len(mistakes),
            "next_recommendation": LearningService._next_step(curated, latest, current, len(mistakes), modules, len(attempts)),
        })
        return state

    @staticmethod
    def _next_step(curated, latest, current, n_mistakes, modules, n_attempts) -> Dict[str, str]:
        if not curated:
            return {"action": "chat", "text": "Ask the mentor a question about this subject."}
        if not latest:
            return {"action": "diagnostic", "text": "Take the 5-question diagnostic to personalise your roadmap."}
        if n_mistakes >= 3:
            return {"action": "revision", "text": f"Revise {n_mistakes} questions you missed before moving on."}
        if current:
            return {"action": "module", "text": f"Study next: {current['title']}", "module_id": current["id"]}
        if modules and all(m["status"] == "completed" for m in modules):
            return {"action": "reassess", "text": "Roadmap complete. Retake the assessment to measure your improvement."}
        return {"action": "chat", "text": "Ask the mentor what to focus on."}

    # ------------------------------------------------------------------ mentor chat
    @staticmethod
    def post_message(user: dict, chat: Dict[str, Any], message: str, mode: str) -> Dict[str, Any]:
        text = message.strip()
        if not text:
            _err(400, "Message cannot be empty.")
        if mode not in MODES:
            _err(400, f"Unknown mode. Use one of: {', '.join(sorted(MODES))}.")
        if chat["status"] != "active":
            _err(409, "This chat is archived. Restore it to continue.")

        history = [{"role": m["role"], "content": m["content"]} for m in LearningRepository.get_messages(chat["id"], 10)]
        st = LearningService.chat_state(chat, user)
        ctx = [f"Subject: {chat['subject_title']}."]
        if st.get("level_note") and st.get("latest_score"):
            ctx.append(f"Diagnostic level: {st['latest_score']['level']} ({st['latest_score']['percentage']}%).")
        if st.get("weaknesses"):
            ctx.append("Weak topics: " + "; ".join(st["weaknesses"][:4]) + ".")
        if st.get("current_module"):
            ctx.append(f"Currently studying: {st['current_module']['title']}.")
        if _MODE_INSTRUCTIONS[mode]:
            ctx.append(_MODE_INSTRUCTIONS[mode])
        ctx.append("Never reveal hidden answer keys. Be honest about uncertainty.")

        try:
            provider = get_ai_provider()
            result = provider.generate_chat_response(
                prompt=text, subject=chat["subject_title"], history=history, learner_context="\n".join(ctx))
            reply = str(result["reply"])
            followups = list(result.get("suggested_followups", []))[:4]
            is_mock = bool(result.get("is_mock", True))
            provider_name = result.get("provider", provider.provider_name)
        except Exception:
            logger.warning("Mentor provider unavailable")  # no secrets are logged: provider hides them
            _err(502, "The AI mentor is temporarily unavailable. Your chat is saved; please try again.")

        notice = _MOCK_MODE_NOTE.get(mode) if is_mock else None
        if is_mock and not st["curated"]:
            notice = "Offline Demo AI has no knowledge of this subject. Configure a live AI provider for open-ended subjects."
        saved = LearningRepository.save_turn(chat["id"], text, reply, followups)
        return {**saved, "is_mock": is_mock, "provider": provider_name, "notice": notice}

    # ------------------------------------------------------------------ diagnostic / reassessment
    @staticmethod
    def assessment_questions(chat: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not curriculum.is_curated(chat["subject_id"]):
            _err(400, "Assessments are only available for curated subjects.")
        qs = Repository.get_assessment_questions(chat["subject_id"])
        return [{k: q[k] for k in ("id", "subject_id", "question_number", "question_text", "option_a", "option_b",
                                   "option_c", "option_d", "topic", "difficulty")} for q in qs]

    @staticmethod
    @atomic_write
    def submit_assessment(user: dict, chat: Dict[str, Any], answers: Dict[str, str]) -> Dict[str, Any]:
        if chat["status"] != "active":
            _err(409, "This chat is archived.")
        if not curriculum.is_curated(chat["subject_id"]):
            _err(400, "Assessments are only available for curated subjects.")
        kind = "reassessment" if LearningRepository.chat_attempts(chat["id"]) else "diagnostic"
        result = run_assessment(user, chat["subject_id"], answers, chat_id=chat["id"], kind=kind)
        result["kind"] = kind
        return result

    # ------------------------------------------------------------------ modules / practice
    @staticmethod
    def _module_in_roadmap(chat: Dict[str, Any], user: dict, module_id: str) -> Dict[str, Any]:
        st = LearningService.chat_state(chat, user)
        if not st["roadmap"]:
            _err(409, "Take the diagnostic first to unlock your roadmap.")
        mod = next((m for m in st["roadmap"]["modules"] if m["id"] == module_id), None)
        if not mod:
            _err(404, "Module is not part of this chat's roadmap.")
        if mod["status"] == "locked":
            _err(409, "Complete the prerequisite modules first.")
        return mod

    @staticmethod
    def get_module(user: dict, chat: Dict[str, Any], module_id: str) -> Dict[str, Any]:
        mod = LearningService._module_in_roadmap(chat, user, module_id)
        content = curriculum.get_module(module_id)
        if not content:
            _err(404, "Lesson content is not available.")
        LearningRepository.mark_lesson_viewed(chat["id"], module_id)
        return {"module": mod, "lesson": content["lesson"],
                "questions": [curriculum.public_question(q) for q in content["questions"]],
                "pass_rule": f"Answer at least {round(curriculum.PASS_RATIO * 100)}% correctly to complete this module."}

    @staticmethod
    @atomic_write
    def submit_practice(user: dict, chat: Dict[str, Any], module_id: str, answers: Dict[str, int]) -> Dict[str, Any]:
        if chat["status"] != "active":
            _err(409, "This chat is archived.")
        mod = LearningService._module_in_roadmap(chat, user, module_id)
        content = curriculum.get_module(module_id)
        if not content:
            _err(404, "Lesson content is not available.")
        questions = content["questions"]
        ids = {q["id"] for q in questions}
        if set(answers) - ids:
            _err(400, "Unknown question id in submission.")
        results = []
        for q in questions:
            if q["id"] not in answers:
                _err(400, "Answer every question before submitting.")
            sel = answers[q["id"]]
            if not isinstance(sel, int) or isinstance(sel, bool) or not 0 <= sel < len(q["options"]):
                _err(400, "Invalid option selected.")
            results.append({"question_id": q["id"], "selected_index": sel, "is_correct": sel == q["answer"]})
        correct = sum(r["is_correct"] for r in results)
        passed = correct / len(questions) >= curriculum.PASS_RATIO - 1e-9
        rec = LearningRepository.record_practice(chat["id"], module_id, results, passed)

        xp_awarded = 0
        if rec["newly_completed"]:
            if CompetitionRepository.record_xp_event(
                    user["id"], f"module.{chat['id']}.{module_id}", MODULE_XP,
                    f"Completed module: {mod['title']}", "learning_module", f"{chat['id']}:{module_id}"):
                xp_awarded = MODULE_XP
            notify(user["id"], "achievement", "Module completed", f"{mod['title']} (+{MODULE_XP} XP)",
                   f"/learn/{chat['id']}", f"module:{chat['id']}:{module_id}")
            from .referral_service import ReferralService
            ReferralService.check_and_qualify_referral(user["id"], "learning_mission")
            LearningService._maybe_issue_track_certificate(user, chat)

        feedback = [{
            "question_id": q["id"], "question": q["question"], "options": q["options"],
            "selected_index": r["selected_index"], "is_correct": r["is_correct"],
            "correct_index": q["answer"], "explanation": q["explanation"],
        } for q, r in zip(questions, results)]
        return {
            "correct": correct, "total": len(questions), "percentage": round(100 * correct / len(questions)),
            "passed": passed, "module_completed": passed, "newly_completed": rec["newly_completed"],
            "xp_awarded": xp_awarded, "feedback": feedback,
            "message": ("Module complete!" if passed else "Not quite yet. Review the explanations and try again; mistakes are saved to your Revision list."),
            "next_recommendation": LearningService.chat_state(chat, user)["next_recommendation"],
        }

    @staticmethod
    def _maybe_issue_track_certificate(user: dict, chat: Dict[str, Any]) -> None:
        try:
            st = LearningService.chat_state(chat, user)
            mods = st["roadmap"]["modules"] if st["roadmap"] else []
            if mods and all(m["status"] == "completed" for m in mods):
                from .certificate_service import CertificateService
                cert = CertificateService.issue_certificate(
                    user_id=user["id"], user_name=user.get("name", "Student"), cert_type="TRACK_COMPLETION",
                    title=f"{chat['subject_title']} Learning Path Completed",
                    description=f"PragyaX Challenge Achievement: completed {len(mods)} roadmap modules with practice scores of at least "
                                f"{round(curriculum.PASS_RATIO * 100)}%. Not an accredited qualification.",
                    metadata={"assessment_id": f"track.{chat['id']}", "chat_id": chat["id"], "modules": len(mods)})
                notify(user["id"], "achievement", "Learning path completed",
                       f"{chat['subject_title']}: achievement issued.", "/certificates", f"track:{chat['id']}")
                return cert  # type: ignore[return-value]
        except Exception:
            logger.exception("track certificate issue failed")

    # ------------------------------------------------------------------ revision
    @staticmethod
    def revision(user: dict, chat: Dict[str, Any]) -> Dict[str, Any]:
        items = []
        for m in LearningRepository.mistakes(chat["id"], 50):
            mod = curriculum.get_module(m["module_id"])
            q = next((q for q in (mod["questions"] if mod else []) if q["id"] == m["question_id"]), None)
            if not q:
                continue
            items.append({"module_id": m["module_id"], "module_title": mod["catalog"]["title"], "question": q["question"],
                          "options": q["options"], "your_answer": q["options"][m["selected_index"]],
                          "correct_answer": q["options"][q["answer"]], "explanation": q["explanation"],
                          "last_missed": m["created_at"]})
        by_module: Dict[str, int] = {}
        for i in items:
            by_module[i["module_title"]] = by_module.get(i["module_title"], 0) + 1
        priorities = sorted(by_module.items(), key=lambda kv: -kv[1])
        return {"items": items, "priorities": [{"module_title": k, "missed": v} for k, v in priorities],
                "suggestion": ("Re-take practice for your top priority module after 1 day, then again after 3 days."
                               if items else "No unresolved mistakes. Nice work.")}

    @staticmethod
    def generate_revision_reminders(user_id: str) -> None:
        """At most one revision reminder per chat per day (de-duplicated, respects preferences/quiet hours)."""
        try:
            for chat in LearningRepository.list_chats(user_id):
                n = len(LearningRepository.mistakes(chat["id"], 50))
                if n:
                    notify(user_id, "revision", "Time to revise",
                           f"{n} missed question(s) in {chat['title']}.", f"/learn/{chat['id']}",
                           f"revision:{chat['id']}:{date.today().isoformat()}")
        except Exception:
            logger.exception("revision reminder failed")

    # ------------------------------------------------------------------ projects
    @staticmethod
    def list_projects(user: dict) -> List[Dict[str, Any]]:
        prog = LearningRepository.list_project_progress(user["id"])
        out = []
        for p in curriculum.PROJECTS:
            pr = prog.get(p["id"]) or {}
            out.append({**p, "subject_title": curriculum.SUBJECT_TITLES[p["subject_id"]],
                        "milestones_done": pr.get("milestones_done", []), "status": pr.get("status", "not_started"),
                        "submission_text": pr.get("submission_text"), "submission_url": pr.get("submission_url"),
                        "reflection_scores": pr.get("reflection_scores"),
                        "evaluation_note": "Self-assessed against the rubric. Not independently verified." if pr.get("status") == "submitted" else None})
        return out

    @staticmethod
    @atomic_write
    def toggle_milestone(user: dict, project_id: str, index: int, done: bool) -> Dict[str, Any]:
        proj = curriculum.get_project(project_id)
        if not proj:
            _err(404, "Project not found.")
        if not 0 <= index < len(proj["milestones"]):
            _err(400, "Invalid milestone.")
        cur = LearningRepository.get_project_progress(user["id"], project_id) or {"milestones_done": [], "status": "in_progress"}
        if cur["status"] == "submitted":
            _err(409, "Project already submitted.")
        ms = set(cur["milestones_done"])
        (ms.add if done else ms.discard)(index)
        LearningRepository.save_project_progress(user["id"], project_id, sorted(ms), "in_progress")
        return next(p for p in LearningService.list_projects(user) if p["id"] == project_id)

    @staticmethod
    @atomic_write
    def submit_project(user: dict, project_id: str, text: str, url: Optional[str], scores: Dict[str, int]) -> Dict[str, Any]:
        proj = curriculum.get_project(project_id)
        if not proj:
            _err(404, "Project not found.")
        cur = LearningRepository.get_project_progress(user["id"], project_id) or {"milestones_done": [], "status": "in_progress"}
        if len(cur["milestones_done"]) < len(proj["milestones"]):
            _err(409, "Complete every milestone before submitting.")
        if cur["status"] == "submitted":
            _err(409, "Project already submitted.")
        if len((text or "").strip()) < 30 and not url:
            _err(400, "Describe your work (at least 30 characters) or add a link.")
        if url and not url.lower().startswith(("http://", "https://")):
            _err(400, "Link must start with http:// or https://.")
        if set(scores) != set(proj["rubric"]) or any(not isinstance(v, int) or not 0 <= v <= 3 for v in scores.values()):
            _err(400, "Rate yourself 0-3 on every rubric criterion.")
        LearningRepository.save_project_progress(user["id"], project_id, cur["milestones_done"], "submitted",
                                                 (text or "").strip()[:4000], (url or None), scores)
        notify(user["id"], "project", "Project submitted", f"{proj['title']} saved as self-assessed evidence.",
               "/projects", f"project:{project_id}")
        return next(p for p in LearningService.list_projects(user) if p["id"] == project_id)

    # ------------------------------------------------------------------ skill profile
    @staticmethod
    def skill_profile(user: dict) -> Dict[str, Any]:
        from .certificate_service import CertificateService
        from .gamification_hub import GamificationHub
        subjects = []
        for chat in LearningRepository.list_chats(user["id"], include_archived=True):
            st = LearningService.chat_state(chat, user)
            mastered = [m for m in (st["roadmap"]["modules"] if st["roadmap"] else []) if m["status"] == "completed"]
            subjects.append({
                "chat_id": chat["id"], "subject_title": chat["subject_title"], "curated": st["curated"],
                "level": st["latest_score"]["level"] if st["latest_score"] else None,
                "latest_percentage": st["latest_score"]["percentage"] if st["latest_score"] else None,
                "improvement": st["improvement"], "weaknesses": st["weaknesses"],
                "modules_completed": st["modules_completed"], "modules_total": st["modules_total"],
                "mastered_topics": [{"title": m["title"], "mastery_percentage": m["mastery_percentage"]} for m in mastered],
            })
        projects = [p for p in LearningService.list_projects(user) if p["status"] == "submitted"]
        return {
            "subjects": subjects,
            "projects": [{"id": p["id"], "title": p["title"], "level": p["level"], "subject_title": p["subject_title"],
                          "rubric_total": sum((p["reflection_scores"] or {}).values()), "rubric_max": 3 * len(p["rubric"]),
                          "evidence_type": "self-assessed"} for p in projects],
            "gamification": GamificationHub.get_user_profile_gamification(user["id"]),
            "badges": Repository.get_user_badges(user["id"]),
            "certificates": CertificateService.get_user_certificates(user["id"]),
            "disclaimer": "Achievements are PragyaX platform records. They are not accredited qualifications; "
                          "projects are self-assessed unless marked otherwise.",
        }


@atomic_write
def run_assessment(user: dict, subject_id: str, raw_answers: Dict[str, str], chat_id: Optional[str] = None,
                   kind: Optional[str] = None, provider_factory=None) -> Dict[str, Any]:
    """Shared by the legacy /assessments/submit and chat-scoped diagnostics. Server-owned grading + rewards."""
    ref_questions = Repository.get_raw_assessment_questions_with_answers(subject_id)
    if not ref_questions or len(ref_questions) != 5:
        _err(400, "Assessment must contain exactly 5 valid questions.")
    unknown = set(raw_answers) - {q["id"] for q in ref_questions}
    if unknown:
        _err(400, f"Unknown question id(s): {', '.join(sorted(unknown))}.")
    for q in ref_questions:
        if q["id"] not in raw_answers:
            _err(400, f"Missing answer for question #{q['question_number']}.")
        ans = str(raw_answers[q["id"]]).strip().upper()
        if ans not in {"A", "B", "C", "D"}:
            _err(400, f"Invalid option '{ans}' for question #{q['question_number']}. Must be A, B, C, or D.")
    answers = {k: str(v).strip().upper() for k, v in raw_answers.items()}
    subject = Repository.get_subject_by_id(ref_questions[0]["subject_id"])
    if subject is None:
        _err(400, "Assessment subject is unavailable.")
    first_for_subject = not any(a["subject_id"] == subject["id"] for a in Repository.get_user_assessment_attempts(user["id"], limit=200))

    try:
        ev = evaluate_assessment((provider_factory or get_ai_provider)(), subject["title"], ref_questions, answers)
    except Exception:
        logger.warning("Assessment provider unavailable")
        _err(502, "Assessment provider is temporarily unavailable.")

    attempt = Repository.save_assessment_attempt(
        user_id=user["id"], subject_id=subject["id"], score=ev["score"], total=ev["total"], percentage=ev["percentage"],
        proficiency_level=ev["proficiency_level"], summary_feedback=ev["summary_feedback"],
        recommended_topics=ev["recommended_topics"], user_answers=answers, breakdown=ev["breakdown"])
    if chat_id:
        LearningRepository.link_attempt(attempt["id"], chat_id, kind or "diagnostic")

    # Rewards: XP only for the first attempt per subject (retakes measure growth, they don't farm XP).
    try:
        if first_for_subject:
            pts = 50 + (50 if ev["percentage"] >= 80 else 0)
            CompetitionRepository.record_xp_event(
                user_id=user["id"], event_key=f"assessment.{attempt['id']}", points=pts,
                reason=f"Completed {subject['title']} diagnostic", source_type="assessment", source_id=attempt["id"])
            if ev["percentage"] >= 80:
                from .certificate_service import CertificateService
                CertificateService.issue_certificate(
                    user_id=user["id"], user_name=user.get("name", "Student"), cert_type="ASSESSMENT",
                    title=f"{subject['title']} Diagnostic: High Score",
                    description=f"PragyaX Challenge Achievement: scored {ev['percentage']}% ({ev['score']}/{ev['total']}) on a short "
                                f"{subject['title']} diagnostic. Not an accredited certification.",
                    metadata={"assessment_id": attempt["id"], "percentage": ev["percentage"]})
        from .referral_service import ReferralService
        ReferralService.check_and_qualify_referral(user["id"], "assessment")  # gated: needs diagnostic AND first mission
    except Exception:
        logger.warning("Assessment transaction could not complete rewards")
        raise

    return {
        "id": attempt["id"], "user_id": user["id"], "subject_id": attempt["subject_id"],
        "subject_title": attempt.get("subject_title", subject["title"]), "score": attempt["score"],
        "total": attempt["total"], "percentage": attempt["percentage"], "proficiency_level": attempt["proficiency_level"],
        "summary_feedback": attempt["summary_feedback"], "recommended_topics": attempt["recommended_topics"],
        "breakdown": attempt["breakdown"], "is_mock": ev.get("is_mock", True), "provider": ev.get("provider", "PragyaX AI"),
        "created_at": attempt.get("created_at"),
    }
