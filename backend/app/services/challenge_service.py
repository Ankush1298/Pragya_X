from ..database.connection import atomic_write
"""
Challenge Management Service
Owned by: Ankush (Gamification & Competition Module Owner)
Reuses: daily_challenge_engine.py, leaderboard_engine.py, gamification_service.py
"""

import uuid
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from ..database.competition_repository import CompetitionRepository
from ..database.repository import Repository
from ..database.connection import get_db
from .daily_challenge_engine import (
    ChallengeDefinition,
    ChallengePool,
    select_daily_challenge,
    to_learner_view
)
from .gamification_service import compute_challenge_reward, reward_event_key
from .leaderboard_engine import LeaderboardMember, LeaderboardScope, ScopeType, rank_members


class ChallengeService:
    @staticmethod
    def get_daily_challenge_for_date(subject_id: str = "subj_python", target_date: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Rotates daily challenge deterministically based on calendar date using daily_challenge_engine.
        Returns learner-facing view (hiding answer key until completed).
        """
        if target_date:
            try:
                target_d = date.fromisoformat(target_date)
            except Exception:
                target_d = date.today()
        else:
            target_d = date.today()
        today_iso = target_d.isoformat()

        all_challenges = CompetitionRepository.get_all_challenges()
        subj_challenges = [c for c in all_challenges if c["subject_id"] == subject_id]

        if not subj_challenges:
            # Never return a raw repository row containing the hidden answer key.
            return {}

        # Convert to ChallengeDefinition objects for daily_challenge_engine
        defs = []
        for c in subj_challenges:
            defs.append(ChallengeDefinition(
                challenge_id=c["id"],
                subject_id=c["subject_id"],
                title=c["title"],
                topic=c["topic"],
                difficulty=c["difficulty"],
                description=c["description"],
                code_snippet=c["code_snippet"],
                option_a=c["option_a"],
                option_b=c["option_b"],
                option_c=c["option_c"],
                option_d=c["option_d"],
                correct_option=c["correct_option"],
                explanation=c["explanation"],
                points=c["points"],
                question_type="multiple_choice"
            ))

        pool = ChallengePool(subject_id=subject_id, challenges=tuple(defs))
        selected_def = select_daily_challenge(pool, target_d)

        has_completed = False
        user_sub = None
        if user_id:
            sub = CompetitionRepository.get_user_challenge_submission(user_id, selected_def.challenge_id)
            if sub:
                has_completed = True
                user_sub = sub

        result = {
            "id": selected_def.challenge_id,
            "subject_id": selected_def.subject_id,
            "challenge_date": today_iso,
            "title": selected_def.title,
            "topic": selected_def.topic,
            "difficulty": selected_def.difficulty,
            "description": selected_def.description,
            "code_snippet": selected_def.code_snippet,
            "option_a": selected_def.option_a,
            "option_b": selected_def.option_b,
            "option_c": selected_def.option_c,
            "option_d": selected_def.option_d,
            "points": selected_def.points,
            "has_completed": has_completed,
            "user_submission": user_sub,
            "correct_option": selected_def.correct_option if has_completed else None,
            "explanation": selected_def.explanation if has_completed else None
        }
        return result

    @staticmethod
    def get_challenge_library(topic: Optional[str] = None, difficulty: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all challenges in the library, indicating completion status for user."""
        challenges = CompetitionRepository.get_all_challenges(topic=topic, difficulty=difficulty)
        results = []
        for c in challenges:
            has_completed = False
            if user_id:
                sub = CompetitionRepository.get_user_challenge_submission(user_id, c["id"])
                has_completed = bool(sub)
            item = {
                "id": c["id"],
                "subject_id": c["subject_id"],
                "title": c["title"],
                "topic": c["topic"],
                "difficulty": c["difficulty"],
                "description": c["description"],
                "code_snippet": c["code_snippet"],
                "option_a": c["option_a"],
                "option_b": c["option_b"],
                "option_c": c["option_c"],
                "option_d": c["option_d"],
                "points": c["points"],
                "has_completed": has_completed,
                "correct_option": c["correct_option"] if has_completed else None,
                "explanation": c["explanation"] if has_completed else None
            }
            results.append(item)
        return results

    @staticmethod
    @atomic_write
    def submit_challenge(user_id: str, challenge_id: str, selected_option: str) -> Dict[str, Any]:
        """
        Validates challenge answer, updates streaks, awards XP via ledger, and issues streak badges.
        Anti-duplicate check: rejects resubmissions.
        """
        chal = CompetitionRepository.get_challenge_by_id(challenge_id)
        if not chal:
            return {"error": "Challenge not found"}

        existing = CompetitionRepository.get_user_challenge_submission(user_id, challenge_id)
        if existing:
            return {"error": "Challenge already completed by this user"}

        correct_opt = chal["correct_option"].strip().upper()
        user_opt = selected_option.strip().upper()
        is_correct = (user_opt == correct_opt)
        points_to_award = chal["points"] if is_correct else 0
        today_iso = date.today().isoformat()

        # Record submission
        CompetitionRepository.record_challenge_submission(
            user_id=user_id,
            challenge_id=challenge_id,
            submitted_answer=user_opt,
            is_correct=is_correct,
            points_awarded=points_to_award,
            completed_date=today_iso
        )

        streak_info = CompetitionRepository.get_user_streak(user_id)
        badges_awarded = []

        if is_correct:
            # 1. Update streak
            streak_info = CompetitionRepository.update_user_streak(user_id, today_iso)

            # 2. Record XP in ledger idempotently
            event_key = reward_event_key(user_id=user_id, source_type="daily_challenge", source_id=challenge_id)
            CompetitionRepository.record_xp_event(
                user_id=user_id,
                event_key=event_key,
                points=points_to_award,
                reason="DAILY_CHALLENGE",
                source_type="daily_challenge",
                source_id=challenge_id
            )

            # 3. Check for streak badges
            streak_days = streak_info.get("current_streak", 1)
            badges_awarded.append("daily_striker")

            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO user_badges (id, user_id, badge_key, title, description, icon)
                    VALUES (?, ?, 'daily_striker', 'Daily Code Breaker', 'Solved today''s code snippet challenge', 'zap')
                    ON CONFLICT (user_id, badge_key) DO NOTHING;
                """, (f"bdg_{uuid.uuid4().hex[:12]}", user_id))

                if streak_days >= 3:
                    cur.execute("""
                        INSERT INTO user_badges (id, user_id, badge_key, title, description, icon)
                        VALUES (?, ?, 'streak_3', '3-Day Hot Streak', 'Solved daily challenges 3 days in a row', 'flame')
                        ON CONFLICT (user_id, badge_key) DO NOTHING;
                    """, (f"bdg_{uuid.uuid4().hex[:12]}", user_id))
                    badges_awarded.append("streak_3")
                if streak_days >= 7:
                    cur.execute("""
                        INSERT INTO user_badges (id, user_id, badge_key, title, description, icon)
                        VALUES (?, ?, 'streak_7', 'Weekly Master', 'Maintained a 7-day challenge streak', 'crown')
                        ON CONFLICT (user_id, badge_key) DO NOTHING;
                    """, (f"bdg_{uuid.uuid4().hex[:12]}", user_id))
                    badges_awarded.append("streak_7")

        return {
            "challenge_id": challenge_id,
            "is_correct": is_correct,
            "points_awarded": points_to_award,
            "correct_option": correct_opt,
            "explanation": chal["explanation"],
            "current_streak": streak_info.get("current_streak", 0),
            "longest_streak": streak_info.get("longest_streak", 0),
            "badges_awarded": badges_awarded
        }

    @staticmethod
    def get_user_streak(user_id: str) -> Dict[str, Any]:
        """Returns current streak metrics."""
        streak = CompetitionRepository.get_user_streak(user_id)
        today_iso = date.today().isoformat()
        active_today = (streak.get("last_activity_date") == today_iso)
        return {
            "current_streak": streak.get("current_streak", 0),
            "longest_streak": streak.get("longest_streak", 0),
            "last_activity_date": streak.get("last_activity_date"),
            "streak_freeze_available": False,
            "active_today": active_today
        }

    @staticmethod
    def get_challenge_history(user_id: str) -> List[Dict[str, Any]]:
        """Returns user's challenge submission history."""
        return CompetitionRepository.get_user_challenge_history(user_id)

    @staticmethod
    def get_challenge_leaderboard(limit: int = 25) -> List[Dict[str, Any]]:
        """Computes leaderboard ranked by challenge completions and points using leaderboard_engine."""
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.user_id, u.name,
                       COALESCE(SUM(s.points_awarded), 0) AS total_points,
                       COUNT(*) AS solved_count,
                       COALESCE(MAX(st.current_streak), 0) AS current_streak
                FROM challenge_submissions s
                JOIN users u ON s.user_id = u.id
                LEFT JOIN user_streaks st ON s.user_id = st.user_id
                WHERE s.is_correct = 1
                GROUP BY s.user_id, u.name
                ORDER BY total_points DESC, current_streak DESC
                LIMIT ?;
            """, (limit,))
            rows = cur.fetchall()

            members = []
            for r in rows:
                members.append(LeaderboardMember(
                    user_id=r["user_id"],
                    display_name=r["name"],
                    total_points=r["total_points"]
                ))

            if not members:
                return []

            ranked = rank_members(members)

            result = []
            for rm in ranked[:limit]:
                # match original row for streak
                orig = next((r for r in rows if r["user_id"] == rm.user_id), None)
                result.append({
                    "rank": rm.rank,
                    "user_id": rm.user_id,
                    "name": rm.display_name,
                    "points": rm.total_points,
                    "streak": orig["current_streak"] if orig else 0,
                    "solved_count": orig["solved_count"] if orig else 0
                })
            return result
