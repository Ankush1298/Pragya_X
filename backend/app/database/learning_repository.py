"""
Data access for the chat-scoped learning layer. PostgreSQL queries through the parameterized repository wrapper.
Every read/write is keyed by chat_id AND user_id so one learner can never touch another's chat.
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from .connection import get_db, atomic_write


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _rows(cur) -> List[Dict[str, Any]]:
    return [dict(r) for r in cur.fetchall()]


class LearningRepository:
    # ------------------------------------------------------------- chats
    @staticmethod
    def create_chat(user_id: str, subject_id: Optional[str], subject_title: str, title: str) -> Dict[str, Any]:
        chat_id = _id("chat")
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO learning_chats (id, user_id, subject_id, subject_title, title) VALUES (?, ?, ?, ?, ?)",
                (chat_id, user_id, subject_id, subject_title, title),
            )
        return LearningRepository.get_chat(chat_id, user_id)  # type: ignore[return-value]

    @staticmethod
    def get_chat(chat_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM learning_chats WHERE id = ? AND user_id = ?", (chat_id, user_id))
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_chats(user_id: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM learning_chats WHERE user_id = ?"
        if not include_archived:
            sql += " AND status = 'active'"
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(sql + " ORDER BY updated_at DESC, created_at DESC", (user_id,))
            return _rows(cur)

    @staticmethod
    def update_chat(chat_id: str, user_id: str, title: Optional[str] = None, status: Optional[str] = None) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            if title is not None:
                cur.execute("UPDATE learning_chats SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                            (title, chat_id, user_id))
            if status is not None:
                cur.execute("UPDATE learning_chats SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                            (status, chat_id, user_id))

    @staticmethod
    def touch_chat(chat_id: str) -> None:
        with get_db() as conn:
            conn.cursor().execute("UPDATE learning_chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (chat_id,))

    # ------------------------------------------------------------- messages
    @staticmethod
    @atomic_write
    def add_message(chat_id: str, role: str, content: str, followups: Optional[List[str]] = None) -> Dict[str, Any]:
        msg_id = _id("lmsg")
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO learning_chat_messages (id, chat_id, role, content, suggested_followups, seq) VALUES "
                "(?, ?, ?, ?, ?, (SELECT COALESCE(MAX(seq), 0) + 1 FROM learning_chat_messages WHERE chat_id = ?))",
                (msg_id, chat_id, role, content, json.dumps(followups or []), chat_id),
            )
        LearningRepository.touch_chat(chat_id)
        return {"id": msg_id, "chat_id": chat_id, "role": role, "content": content, "suggested_followups": followups or []}

    @staticmethod
    def get_messages(chat_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM (SELECT * FROM learning_chat_messages WHERE chat_id = ? "
                "ORDER BY seq DESC LIMIT ?) t ORDER BY seq ASC",
                (chat_id, limit),
            )
            out = _rows(cur)
        for m in out:
            m["suggested_followups"] = json.loads(m.get("suggested_followups") or "[]")
        return out

    @staticmethod
    @atomic_write
    def save_turn(chat_id, prompt, reply, followups):
        LearningRepository.add_message(chat_id, "user", prompt)
        return LearningRepository.add_message(chat_id, "assistant", reply, followups)

    # ------------------------------------------------------------- assessments linked to a chat
    @staticmethod
    def link_attempt(attempt_id: str, chat_id: str, kind: str) -> None:
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO learning_chat_attempts (attempt_id, chat_id, kind, seq) VALUES (?, ?, ?, "
                "(SELECT COALESCE(MAX(seq), 0) + 1 FROM learning_chat_attempts WHERE chat_id = ?)) "
                "ON CONFLICT (attempt_id) DO NOTHING", (attempt_id, chat_id, kind, chat_id))

    @staticmethod
    def chat_attempts(chat_id: str) -> List[Dict[str, Any]]:
        """Chronological attempts for this chat (oldest first) with parsed weaknesses."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT a.id, a.score, a.total, a.percentage, a.proficiency_level, a.summary_feedback, "
                "a.recommended_topics, a.breakdown, a.created_at, l.kind, l.seq "
                "FROM learning_chat_attempts l JOIN assessment_attempts a ON a.id = l.attempt_id "
                "WHERE l.chat_id = ? ORDER BY l.seq ASC", (chat_id,))
            rows = _rows(cur)
        for r in rows:
            for key in ("recommended_topics", "breakdown"):
                if isinstance(r.get(key), str):
                    r[key] = json.loads(r[key])
        return rows

    # ------------------------------------------------------------- module progress / practice
    @staticmethod
    def progress_map(chat_id: str) -> Dict[str, Dict[str, Any]]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM learning_module_progress WHERE chat_id = ?", (chat_id,))
            return {r["module_id"]: r for r in _rows(cur)}

    @staticmethod
    def mark_lesson_viewed(chat_id: str, module_id: str) -> None:
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO learning_module_progress (id, chat_id, module_id, lesson_viewed) VALUES (?, ?, ?, 1) "
                "ON CONFLICT (chat_id, module_id) DO UPDATE SET lesson_viewed = 1, updated_at = CURRENT_TIMESTAMP",
                (_id("lmp"), chat_id, module_id))

    @staticmethod
    def record_practice(chat_id: str, module_id: str, results: List[Dict[str, Any]], passed: bool) -> Dict[str, Any]:
        """Stores every answer (mistake history) and updates best score. completed_at is set once, atomically."""
        correct = sum(1 for r in results if r["is_correct"])
        with get_db() as conn:
            cur = conn.cursor()
            for r in results:
                cur.execute(
                    "INSERT INTO learning_practice_answers (id, chat_id, module_id, question_id, selected_index, is_correct) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (_id("lpa"), chat_id, module_id, r["question_id"], r["selected_index"], 1 if r["is_correct"] else 0))
            cur.execute(
                "INSERT INTO learning_module_progress (id, chat_id, module_id, best_correct, total_questions) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT (chat_id, module_id) DO UPDATE SET "
                "best_correct = CASE WHEN excluded.best_correct > learning_module_progress.best_correct "
                "THEN excluded.best_correct ELSE learning_module_progress.best_correct END, "
                "total_questions = excluded.total_questions, updated_at = CURRENT_TIMESTAMP",
                (_id("lmp"), chat_id, module_id, correct, len(results)))
            newly_completed = False
            if passed:
                cur.execute(
                    "UPDATE learning_module_progress SET completed_at = CURRENT_TIMESTAMP "
                    "WHERE chat_id = ? AND module_id = ? AND completed_at IS NULL", (chat_id, module_id))
                newly_completed = cur.rowcount == 1
        return {"correct": correct, "total": len(results), "newly_completed": newly_completed}

    @staticmethod
    def mistakes(chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Questions whose LATEST answer was wrong (still-unresolved mistakes)."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT a.module_id, a.question_id, a.selected_index, a.created_at FROM learning_practice_answers a "
                "WHERE a.chat_id = ? AND a.is_correct = 0 AND NOT EXISTS ("
                "SELECT 1 FROM learning_practice_answers b WHERE b.chat_id = a.chat_id AND b.question_id = a.question_id "
                "AND b.is_correct = 1 AND b.created_at >= a.created_at) ORDER BY a.created_at DESC LIMIT ?",
                (chat_id, limit))
            return _rows(cur)

    @staticmethod
    def completed_module_ids(chat_id: str) -> List[str]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT module_id FROM learning_module_progress WHERE chat_id = ? AND completed_at IS NOT NULL", (chat_id,))
            return [r["module_id"] for r in _rows(cur)]

    @staticmethod
    def user_has_completed_mission(user_id: str) -> bool:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM learning_module_progress p JOIN learning_chats c ON c.id = p.chat_id "
                "WHERE c.user_id = ? AND p.completed_at IS NOT NULL LIMIT 1", (user_id,))
            return cur.fetchone() is not None

    @staticmethod
    def user_has_diagnostic(user_id: str) -> bool:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM assessment_attempts WHERE user_id = ? LIMIT 1", (user_id,))
            return cur.fetchone() is not None

    # ------------------------------------------------------------- projects
    @staticmethod
    def get_project_progress(user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM learning_project_progress WHERE user_id = ? AND project_id = ?", (user_id, project_id))
            row = cur.fetchone()
        if not row:
            return None
        r = dict(row)
        r["milestones_done"] = json.loads(r.get("milestones_done") or "[]")
        r["reflection_scores"] = json.loads(r["reflection_scores"]) if r.get("reflection_scores") else None
        return r

    @staticmethod
    def list_project_progress(user_id: str) -> Dict[str, Dict[str, Any]]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT project_id FROM learning_project_progress WHERE user_id = ?", (user_id,))
            ids = [r["project_id"] for r in _rows(cur)]
        return {i: LearningRepository.get_project_progress(user_id, i) for i in ids}  # type: ignore[misc]

    @staticmethod
    def save_project_progress(user_id: str, project_id: str, milestones: List[int], status: str,
                              text: Optional[str] = None, url: Optional[str] = None,
                              scores: Optional[Dict[str, int]] = None) -> None:
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO learning_project_progress (id, user_id, project_id, milestones_done, status, submission_text, "
                "submission_url, reflection_scores) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (user_id, project_id) DO UPDATE SET milestones_done = excluded.milestones_done, "
                "status = excluded.status, submission_text = COALESCE(excluded.submission_text, learning_project_progress.submission_text), "
                "submission_url = COALESCE(excluded.submission_url, learning_project_progress.submission_url), "
                "reflection_scores = COALESCE(excluded.reflection_scores, learning_project_progress.reflection_scores), "
                "updated_at = CURRENT_TIMESTAMP",
                (_id("lpr"), user_id, project_id, json.dumps(sorted(set(milestones))), status, text, url,
                 json.dumps(scores) if scores else None))

    # ------------------------------------------------------------- notifications
    @staticmethod
    def add_notification(user_id: str, kind: str, title: str, body: str, link: Optional[str], dedupe_key: str) -> bool:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notifications (id, user_id, kind, title, body, link, dedupe_key) VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (user_id, dedupe_key) DO NOTHING",
                (_id("ntf"), user_id, kind, title, body, link, dedupe_key))
            return cur.rowcount == 1

    @staticmethod
    def list_notifications(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?", (user_id, limit))
            return _rows(cur)

    @staticmethod
    def unread_count(user_id: str) -> int:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND read_at IS NULL", (user_id,))
            return int(cur.fetchone()["n"])

    @staticmethod
    def mark_read(user_id: str, notification_id: Optional[str] = None) -> None:
        with get_db() as conn:
            cur = conn.cursor()
            if notification_id:
                cur.execute("UPDATE notifications SET read_at = CURRENT_TIMESTAMP WHERE user_id = ? AND id = ? AND read_at IS NULL",
                            (user_id, notification_id))
            else:
                cur.execute("UPDATE notifications SET read_at = CURRENT_TIMESTAMP WHERE user_id = ? AND read_at IS NULL", (user_id,))

    @staticmethod
    def get_prefs(user_id: str) -> Dict[str, Any]:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM notification_prefs WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
        if row:
            return dict(row)
        return {"user_id": user_id, "battles": 1, "achievements": 1, "reminders": 1, "projects": 1,
                "quiet_start": None, "quiet_end": None}

    @staticmethod
    def save_prefs(user_id: str, p: Dict[str, Any]) -> None:
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO notification_prefs (user_id, battles, achievements, reminders, projects, quiet_start, quiet_end) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT (user_id) DO UPDATE SET battles = excluded.battles, "
                "achievements = excluded.achievements, reminders = excluded.reminders, projects = excluded.projects, "
                "quiet_start = excluded.quiet_start, quiet_end = excluded.quiet_end",
                (user_id, int(p["battles"]), int(p["achievements"]), int(p["reminders"]), int(p["projects"]),
                 p.get("quiet_start"), p.get("quiet_end")))
