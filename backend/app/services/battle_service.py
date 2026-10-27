from ..database.connection import atomic_write
"""
1v1 Battle Service
Owned by: Ankush (Gamification & Competition Module Owner)
Reuses: battle_engine.py, leaderboard_engine.py, gamification_service.py
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from ..database.competition_repository import CompetitionRepository
from .notification_service import notify
from ..database.repository import Repository
from ..database.connection import get_db
from .battle_engine import (
    BattleConfig,
    BattleParticipant,
    BattleQuestion,
    BattleState,
    BattleStatus,
    BattleOutcome,
    AnswerSubmission,
    create_battle,
    start_battle,
    submit_answers as engine_submit_answers,
    battle_view as engine_battle_view,
    score_battle
)
from .leaderboard_engine import LeaderboardMember, rank_members


class BattleService:
    @staticmethod
    def send_invitation(sender_id: str, sender_name: str, recipient_identifier: str, subject_id: str = "subj_python") -> Dict[str, Any]:
        """
        Sends a battle invitation to another student by email or ID.
        Rejects self-invitations and nonexistent users.
        """
        target_user = None
        if "@" in recipient_identifier:
            target_user = Repository.get_user_by_email(recipient_identifier)
        else:
            target_user = Repository.get_user_by_id(recipient_identifier)

        if not target_user:
            return {"error": f"Student '{recipient_identifier}' not found."}

        recipient_id = target_user["id"]
        recipient_name = target_user["name"]

        if sender_id == recipient_id:
            return {"error": "You cannot challenge yourself to a battle."}

        invitation = CompetitionRepository.create_battle_invitation(
            sender_id=sender_id,
            sender_name=sender_name,
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            subject_id=subject_id
        )
        if isinstance(invitation, dict) and invitation.get("id"):
            notify(recipient_id, "battle", "Battle invitation", f"{sender_name} challenged you to a 1v1 battle.",
                   "/battles", f"battle_invite:{invitation['id']}")
        return {"invitation": invitation}

    @staticmethod
    @atomic_write
    def respond_to_invitation(user_id: str, invitation_id: str, accept: bool) -> Dict[str, Any]:
        """
        Accepts or rejects an invitation.
        If accepted, automatically sets up the 1v1 battle lobby with questions.
        """
        inv = CompetitionRepository.get_invitation_by_id(invitation_id)
        if not inv:
            return {"error": "Invitation not found."}

        if inv["recipient_id"] != user_id:
            return {"error": "Unauthorized: This invitation was not addressed to you."}

        if inv["status"] != "PENDING":
            return {"error": f"Invitation is already {inv['status']}."}

        if not accept:
            updated = CompetitionRepository.update_invitation_status(invitation_id, "REJECTED")
            return {"status": "REJECTED", "invitation": updated}

        # Accept -> Create battle lobby
        battle_id = f"btl_{uuid.uuid4().hex[:10]}"
        raw_questions = Repository.get_raw_assessment_questions_with_answers(inv["subject_id"])
        if not raw_questions:
            return {"error": "No questions available for battle subject."}

        # Build battle questions list
        questions_payload = []
        for q in raw_questions[:5]:
            questions_payload.append({
                "question_id": q["id"],
                "question_text": q["question_text"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
                "correct_option": q["correct_option"],
                "explanation": q["explanation"],
                "topic": q["topic"]
            })

        battle = CompetitionRepository.create_battle(
            battle_id=battle_id,
            p1_id=inv["sender_id"],
            p1_name=inv["sender_name"],
            p2_id=inv["recipient_id"],
            p2_name=inv["recipient_name"],
            subject_id=inv["subject_id"],
            questions=questions_payload
        )

        CompetitionRepository.update_invitation_status(invitation_id, "ACCEPTED", battle_id=battle_id)

        return {
            "status": "ACCEPTED",
            "battle_id": battle_id,
            "battle": BattleService.get_battle_view(user_id, battle_id)
        }

    @staticmethod
    @atomic_write
    def set_player_ready(user_id: str, battle_id: str) -> Dict[str, Any]:
        """
        Marks player ready. If both players are ready, starts the battle.
        """
        battle = CompetitionRepository.get_battle_by_id(battle_id)
        if not battle:
            return {"error": "Battle not found."}

        if user_id not in (battle["player_one_id"], battle["player_two_id"]):
            return {"error": "Unauthorized participant."}

        if battle["status"] != "CREATED":
            return {"error": f"Cannot ready up in '{battle['status']}' state."}

        updates = {}
        if user_id == battle["player_one_id"]:
            updates["player_one_ready"] = 1
            p1_ready = True
            p2_ready = bool(battle["player_two_ready"])
        else:
            updates["player_two_ready"] = 1
            p1_ready = bool(battle["player_one_ready"])
            p2_ready = True

        # Check if both ready -> start battle!
        if p1_ready and p2_ready:
            updates["status"] = "ACTIVE"
            updates["started_at"] = datetime.now(timezone.utc).isoformat()

        updated_battle = CompetitionRepository.update_battle_state(battle_id, updates)
        return {"battle": BattleService.get_battle_view(user_id, battle_id)}

    @staticmethod
    def get_battle_view(user_id: str, battle_id: str) -> Dict[str, Any]:
        """
        Returns learner-safe battle snapshot using battle_engine.battle_view.
        Hides opponent's choices, answer keys, and results until COMPLETED!
        """
        battle = CompetitionRepository.get_battle_by_id(battle_id)
        if not battle:
            return {"error": "Battle not found."}

        if user_id not in (battle["player_one_id"], battle["player_two_id"]):
            return {"error": "Unauthorized: Not a participant in this battle."}

        # Build BattleConfig and participants
        b_questions = tuple(
            BattleQuestion(
                question_id=q["question_id"],
                question_text=q["question_text"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_option=q["correct_option"],
                explanation=q["explanation"],
                topic=q["topic"]
            )
            for q in battle["questions"]
        )
        config = BattleConfig(battle_id=battle_id, questions=b_questions)
        p1 = BattleParticipant(user_id=battle["player_one_id"], display_name=battle["player_one_name"])
        p2 = BattleParticipant(user_id=battle["player_two_id"], display_name=battle["player_two_name"])

        # Reconstruct state
        state = create_battle(config, p1, p2)
        if battle["status"] in ("ACTIVE", "COMPLETED"):
            state = start_battle(state)

        # Apply submissions if present
        p1_ans = battle.get("player_one_answers") or {}
        if p1_ans:
            submissions_p1 = [AnswerSubmission(q_id, opt) for q_id, opt in p1_ans.items()]
            state = engine_submit_answers(state, p1.user_id, submissions_p1)

        p2_ans = battle.get("player_two_answers") or {}
        if p2_ans:
            submissions_p2 = [AnswerSubmission(q_id, opt) for q_id, opt in p2_ans.items()]
            state = engine_submit_answers(state, p2.user_id, submissions_p2)

        # Generate participant-safe view
        view = engine_battle_view(state, user_id)

        return {
            "battle_id": view.battle_id,
            "status": view.status.value.upper(),
            "viewer_user_id": view.viewer_user_id,
            "opponent_display_name": view.opponent_display_name,
            "viewer_submitted": view.viewer_submitted,
            "opponent_submitted": view.opponent_submitted,
            "started_at": battle.get("started_at"),
            "time_limit_seconds": 60,
            "questions": [
                {
                    "position": q.position,
                    "question_id": q.question_id,
                    "question_text": q.question_text,
                    "option_a": q.option_a,
                    "option_b": q.option_b,
                    "option_c": q.option_c,
                    "option_d": q.option_d,
                    "topic": q.topic
                }
                for q in view.questions
            ],
            "viewer_answers": dict(view.viewer_answers),
            "result": {
                "outcome": view.result.outcome.value.upper(),
                "winner_user_id": view.result.winner_user_id,
                "scores": [
                    {"user_id": s.user_id, "correct": s.correct, "answered": s.answered, "total": s.total}
                    for s in view.result.scores
                ]
            } if view.result else None,
            "review": [
                {
                    "position": r.position,
                    "question_id": r.question_id,
                    "correct_option": r.correct_option,
                    "explanation": r.explanation,
                    "answers": dict(r.answers)
                }
                for r in view.review
            ] if view.review else []
        }

    @staticmethod
    @atomic_write
    def submit_battle_answers(user_id: str, battle_id: str, answers: Dict[str, str], time_taken_seconds: float = 0.0) -> Dict[str, Any]:
        """
        Submits participant's answer sheet.
        Validates choices server-side against authoritative question keys.
        When both players submit, computes scores, determines winner, awards XP idempotently,
        updates win/loss stats, awards achievement badges, and issues champion certificate if milestone reached!
        """
        battle = CompetitionRepository.get_battle_by_id(battle_id)
        if not battle:
            return {"error": "Battle not found."}

        if user_id not in (battle["player_one_id"], battle["player_two_id"]):
            return {"error": "Unauthorized participant."}

        if battle["status"] != "ACTIVE":
            return {"error": f"Cannot submit answers in '{battle['status']}' state."}

        is_p1 = (user_id == battle["player_one_id"])
        existing_answers = battle["player_one_answers"] if is_p1 else battle["player_two_answers"]
        if existing_answers:
            return {"error": "You have already submitted answers for this battle."}

        allowed_ids = {q["question_id"] for q in battle["questions"]}
        if not answers or any(k not in allowed_ids or v.strip().upper() not in {"A","B","C","D"} for k,v in answers.items()):
            return {"error": "Submit a non-empty answer sheet containing valid question IDs and options."}
        started = battle.get("started_at")
        if started:
            start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            elapsed = max(0, (datetime.now(timezone.utc) - start_dt).total_seconds())
            if elapsed > 65:
                return {"error": "Battle time limit expired. Start a rematch to try again."}
            time_taken_seconds = elapsed

        # Normalize answers
        normalized_answers = {k: v.strip().upper() for k, v in answers.items()}

        updates = {}
        if is_p1:
            updates["player_one_answers"] = normalized_answers
            updates["player_one_time"] = time_taken_seconds
            p1_ans = normalized_answers
            p2_ans = battle.get("player_two_answers") or {}
        else:
            updates["player_two_answers"] = normalized_answers
            updates["player_two_time"] = time_taken_seconds
            p1_ans = battle.get("player_one_answers") or {}
            p2_ans = normalized_answers

        # Check if both have now submitted -> Finalize and score battle!
        both_submitted = bool(p1_ans and p2_ans)
        if both_submitted:
            b_questions = tuple(
                BattleQuestion(
                    question_id=q["question_id"],
                    question_text=q["question_text"],
                    option_a=q["option_a"],
                    option_b=q["option_b"],
                    option_c=q["option_c"],
                    option_d=q["option_d"],
                    correct_option=q["correct_option"],
                    explanation=q["explanation"],
                    topic=q["topic"]
                )
                for q in battle["questions"]
            )
            config = BattleConfig(battle_id=battle_id, questions=b_questions)
            p1 = BattleParticipant(user_id=battle["player_one_id"], display_name=battle["player_one_name"])
            p2 = BattleParticipant(user_id=battle["player_two_id"], display_name=battle["player_two_name"])

            # Compute official server score
            state = create_battle(config, p1, p2)
            state = start_battle(state)
            state = engine_submit_answers(state, p1.user_id, [AnswerSubmission(k, v) for k, v in p1_ans.items()])
            state = engine_submit_answers(state, p2.user_id, [AnswerSubmission(k, v) for k, v in p2_ans.items()])

            result = state.result
            winner_id = result.winner_user_id
            outcome_val = result.outcome.value

            updates["status"] = "COMPLETED"
            updates["winner_id"] = winner_id
            updates["outcome"] = outcome_val
            updates["completed_at"] = datetime.now(timezone.utc).isoformat()
            updates["result_json"] = {
                "outcome": outcome_val,
                "winner_user_id": winner_id,
                "scores": [
                    {"user_id": s.user_id, "correct": s.correct, "answered": s.answered, "total": s.total}
                    for s in result.scores
                ]
            }

            # Award XP & Badges
            BattleService._distribute_battle_rewards(battle_id, p1, p2, result)

        CompetitionRepository.update_battle_state(battle_id, updates)
        return BattleService.get_battle_view(user_id, battle_id)

    @staticmethod
    def _distribute_battle_rewards(battle_id: str, p1: BattleParticipant, p2: BattleParticipant, result):
        """Awards XP, badges, and checks certificate milestones on battle completion."""
        outcome = result.outcome
        winner_id = result.winner_user_id
        for me, other in ((p1, p2), (p2, p1)):
            verdict = ("tied" if outcome == BattleOutcome.TIE else "won" if winner_id == me.user_id else "lost")
            notify(me.user_id, "battle", "Battle result", f"You {verdict} against {other.display_name}.",
                   f"/battles/{battle_id}", f"battle_result:{battle_id}:{me.user_id}")

        if outcome == BattleOutcome.TIE:
            # Tie: 50 XP each
            CompetitionRepository.record_xp_event(p1.user_id, f"battle.{battle_id}.{p1.user_id}", 50, "BATTLE_TIE", "battle", battle_id)
            CompetitionRepository.record_xp_event(p2.user_id, f"battle.{battle_id}.{p2.user_id}", 50, "BATTLE_TIE", "battle", battle_id)
            CompetitionRepository.update_battle_stats(p1.user_id, is_win=False, is_tie=True, xp_delta=50)
            CompetitionRepository.update_battle_stats(p2.user_id, is_win=False, is_tie=True, xp_delta=50)
        else:
            loser_id = p2.user_id if winner_id == p1.user_id else p1.user_id
            winner_name = p1.display_name if winner_id == p1.user_id else p2.display_name

            # Winner gets 100 XP, loser gets 25 XP consolation
            CompetitionRepository.record_xp_event(winner_id, f"battle.{battle_id}.{winner_id}", 100, "BATTLE_VICTORY", "battle", battle_id)
            CompetitionRepository.record_xp_event(loser_id, f"battle.{battle_id}.{loser_id}", 25, "BATTLE_PARTICIPATION", "battle", battle_id)

            w_stats = CompetitionRepository.update_battle_stats(winner_id, is_win=True, is_tie=False, xp_delta=100)
            l_stats = CompetitionRepository.update_battle_stats(loser_id, is_win=False, is_tie=False, xp_delta=25)

            # Badges
            with get_db() as conn:
                cur = conn.cursor()
                # First blood badge for 1st win
                cur.execute("""
                    INSERT INTO user_badges (id, user_id, badge_key, title, description, icon)
                    VALUES (?, ?, 'first_blood', 'First Blood: Duelist', 'Won your first 1v1 student battle', 'swords')
                    ON CONFLICT (user_id, badge_key) DO NOTHING;
                """, (f"bdg_{uuid.uuid4().hex[:12]}", winner_id))

                if w_stats.get("win_streak", 0) >= 3:
                    cur.execute("""
                        INSERT INTO user_badges (id, user_id, badge_key, title, description, icon)
                        VALUES (?, ?, 'duel_master', 'Duel Master: 3-Streak', 'Won 3 consecutive 1v1 battles', 'shield')
                        ON CONFLICT (user_id, badge_key) DO NOTHING;
                    """, (f"bdg_{uuid.uuid4().hex[:12]}", winner_id))

            # Issue 1v1 Battle Winner Certificate
            opponent_display = p2.display_name if winner_id == p1.user_id else p1.display_name
            CompetitionRepository.issue_certificate(
                user_id=winner_id,
                user_name=winner_name,
                cert_type="BATTLE_WINNER",
                title="1v1 Battle Victor",
                description=f"Victory in PragyaX 1v1 Battle against {opponent_display}",
                metadata={"battle_id": battle_id, "total_wins": w_stats.get("wins", 1)}
            )

    @staticmethod
    def rematch(user_id: str, user_name: str, battle_id: str) -> Dict[str, Any]:
        """Creates a new invitation challenging the same opponent to a rematch."""
        battle = CompetitionRepository.get_battle_by_id(battle_id)
        if not battle:
            return {"error": "Battle not found."}
        if user_id not in (battle["player_one_id"], battle["player_two_id"]):
            return {"error": "Unauthorized participant."}

        opponent_id = battle["player_two_id"] if user_id == battle["player_one_id"] else battle["player_one_id"]
        opponent_name = battle["player_two_name"] if user_id == battle["player_one_id"] else battle["player_one_name"]

        inv = CompetitionRepository.create_battle_invitation(
            sender_id=user_id,
            sender_name=user_name,
            recipient_id=opponent_id,
            recipient_name=opponent_name,
            subject_id=battle.get("subject_id", "subj_python")
        )
        return {"invitation": inv}

    @staticmethod
    def get_user_battle_history(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves the user's battles as a SAFE summary: no question bank, answer keys or opponent answers."""
        out = []
        for b in CompetitionRepository.get_user_battles(user_id, limit=limit):
            mine_is_p1 = b["player_one_id"] == user_id
            result = b.get("result") or {}
            out.append({
                "id": b["id"],
                "status": b["status"],
                "subject_id": b.get("subject_id"),
                "opponent_name": b["player_two_name"] if mine_is_p1 else b["player_one_name"],
                "you_ready": bool(b["player_one_ready"] if mine_is_p1 else b["player_two_ready"]),
                "opponent_ready": bool(b["player_two_ready"] if mine_is_p1 else b["player_one_ready"]),
                "outcome": b.get("outcome"),
                "you_won": bool(b.get("winner_id") and b["winner_id"] == user_id),
                "scores": result.get("scores"),
                "created_at": b.get("created_at"),
                "completed_at": b.get("completed_at"),
            })
        return out

    @staticmethod
    def get_battle_leaderboard(limit: int = 25) -> List[Dict[str, Any]]:
        """Ranks players by battle wins and battle XP."""
        stats = CompetitionRepository.get_battle_leaderboard(limit=limit)
        ranked = []
        for rank, s in enumerate(stats, start=1):
            tot = s["total_battles"]
            win_rate = round((s["wins"] / tot * 100), 1) if tot > 0 else 0.0
            ranked.append({
                "rank": rank,
                "user_id": s["user_id"],
                "name": s["name"],
                "wins": s["wins"],
                "losses": s["losses"],
                "ties": s["ties"],
                "win_rate": win_rate,
                "win_streak": s["win_streak"],
                "battle_xp": s["battle_xp"]
            })
        return ranked
