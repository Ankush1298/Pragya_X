"""
PragyaX Competition, Battle, Gamification, Referral & Certificate Repository
Owned by: Ankush (Gamification & Competition Module Owner)
PostgreSQL data access; schema evolves exclusively through versioned migrations.
"""

import json
import uuid
import hashlib
from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional
from .connection import get_db, atomic_write
from ..config import settings


def init_competition_tables():
    """Compatibility entry point. Schema and catalog are managed by SQL migrations."""
    return None


class CompetitionRepository:
    """DAO for Challenges, Battles, Organizations, Competitions, Referrals, Certificates & Gamification."""

    # =========================================================================
    # A. CHALLENGE MANAGEMENT
    # =========================================================================

    @staticmethod
    def get_all_challenges(topic: Optional[str] = None, difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM challenge_library WHERE is_active = 1"
            params = []
            if topic:
                query += " AND topic = ?"
                params.append(topic)
            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty)
            query += " ORDER BY created_at DESC;"
            cur.execute(query, tuple(params))
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def get_challenge_by_id(challenge_id: str) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM challenge_library WHERE id = ?;", (challenge_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def create_challenge(data: Dict[str, Any]) -> Dict[str, Any]:
        init_competition_tables()
        cid = data.get("id") or f"chal_{uuid.uuid4().hex[:10]}"
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO challenge_library (
                    id, subject_id, title, topic, difficulty, description, code_snippet,
                    option_a, option_b, option_c, option_d, correct_option, explanation,
                    points, is_active, scheduled_date, created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                cid, data["subject_id"], data["title"], data["topic"], data["difficulty"],
                data["description"], data["code_snippet"], data["option_a"], data["option_b"],
                data["option_c"], data["option_d"], data["correct_option"].strip().upper(),
                data["explanation"], data.get("points", 50), data.get("is_active", 1),
                data.get("scheduled_date"), data.get("created_by", "admin")
            ))
        return CompetitionRepository.get_challenge_by_id(cid)

    @staticmethod
    def update_challenge(challenge_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        allowed = {"title", "topic", "difficulty", "description", "code_snippet", "option_a", "option_b", "option_c", "option_d", "correct_option", "explanation", "points", "is_active", "scheduled_date"}
        fields = [f"{k} = ?" for k in updates if k in allowed]
        if not fields:
            return CompetitionRepository.get_challenge_by_id(challenge_id)
        values = [updates[k] for k in updates if k in allowed] + [challenge_id]
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE challenge_library SET {', '.join(fields)} WHERE id = ?;", tuple(values))
        return CompetitionRepository.get_challenge_by_id(challenge_id)

    @staticmethod
    def get_user_challenge_submission(user_id: str, challenge_id: str) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM challenge_submissions WHERE user_id = ? AND challenge_id = ?;", (user_id, challenge_id))
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def record_challenge_submission(user_id: str, challenge_id: str, submitted_answer: str, is_correct: bool, points_awarded: int, completed_date: str) -> Dict[str, Any]:
        init_competition_tables()
        sub_id = f"csub_{uuid.uuid4().hex[:12]}"
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO challenge_submissions (
                    id, user_id, challenge_id, submitted_answer, is_correct, points_awarded, completed_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (user_id, challenge_id) DO NOTHING;
            """, (sub_id, user_id, challenge_id, submitted_answer.strip().upper(), 1 if is_correct else 0, points_awarded, completed_date))
        return CompetitionRepository.get_user_challenge_submission(user_id, challenge_id)

    @staticmethod
    def get_user_challenge_history(user_id: str) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.*, c.title, c.topic, c.difficulty
                FROM challenge_submissions s
                JOIN challenge_library c ON s.challenge_id = c.id
                WHERE s.user_id = ?
                ORDER BY s.submitted_at DESC;
            """, (user_id,))
            return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # STREAKS
    # =========================================================================

    @staticmethod
    def get_user_streak(user_id: str) -> Dict[str, Any]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM user_streaks WHERE user_id = ?;", (user_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return {"user_id": user_id, "current_streak": 0, "longest_streak": 0, "last_activity_date": None}

    @staticmethod
    def update_user_streak(user_id: str, activity_date: str) -> Dict[str, Any]:
        init_competition_tables()
        current = CompetitionRepository.get_user_streak(user_id)
        last_date = current.get("last_activity_date")
        curr_streak = current.get("current_streak", 0)
        max_streak = current.get("longest_streak", 0)

        if not last_date:
            new_curr = 1
        elif last_date == activity_date:
            new_curr = curr_streak  # Same day activity does not advance or reset
        else:
            try:
                prev_d = date.fromisoformat(last_date)
                today_d = date.fromisoformat(activity_date)
                delta = (today_d - prev_d).days
                if delta == 1:
                    new_curr = curr_streak + 1
                else:
                    new_curr = 1
            except Exception:
                new_curr = 1

        new_max = max(max_streak, new_curr)

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_activity_date, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    current_streak = excluded.current_streak,
                    longest_streak = excluded.longest_streak,
                    last_activity_date = excluded.last_activity_date,
                    updated_at = CURRENT_TIMESTAMP;
            """, (user_id, new_curr, new_max, activity_date))

        return {"user_id": user_id, "current_streak": new_curr, "longest_streak": new_max, "last_activity_date": activity_date}

    # =========================================================================
    # B. 1V1 BATTLE SYSTEM
    # =========================================================================

    @staticmethod
    def create_battle_invitation(sender_id: str, sender_name: str, recipient_id: str, recipient_name: str, subject_id: str = "subj_python") -> Dict[str, Any]:
        init_competition_tables()
        inv_id = f"binv_{uuid.uuid4().hex[:10]}"
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO battle_invitations (id, sender_id, sender_name, recipient_id, recipient_name, subject_id, status)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING');
            """, (inv_id, sender_id, sender_name, recipient_id, recipient_name, subject_id))
        return CompetitionRepository.get_invitation_by_id(inv_id)

    @staticmethod
    def get_invitation_by_id(inv_id: str) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM battle_invitations WHERE id = ?;", (inv_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_invitation_status(inv_id: str, status: str, battle_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE battle_invitations SET status = ?, battle_id = COALESCE(?, battle_id) WHERE id = ?;", (status, battle_id, inv_id))
        return CompetitionRepository.get_invitation_by_id(inv_id)

    @staticmethod
    def get_user_invitations(user_id: str) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM battle_invitations WHERE recipient_id = ? OR sender_id = ? ORDER BY created_at DESC;", (user_id, user_id))
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def create_battle(battle_id: str, p1_id: str, p1_name: str, p2_id: str, p2_name: str, subject_id: str, questions: list) -> Dict[str, Any]:
        init_competition_tables()
        q_json = json.dumps(questions)
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO battles (
                    id, player_one_id, player_one_name, player_two_id, player_two_name,
                    subject_id, status, questions_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'CREATED', ?, CURRENT_TIMESTAMP);
            """, (battle_id, p1_id, p1_name, p2_id, p2_name, subject_id, q_json))
        return CompetitionRepository.get_battle_by_id(battle_id)

    @staticmethod
    def get_battle_by_id(battle_id: str) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM battles WHERE id = ?;", (battle_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["questions"] = json.loads(res["questions_json"])
            res["player_one_answers"] = json.loads(res["player_one_answers"] or "{}")
            res["player_two_answers"] = json.loads(res["player_two_answers"] or "{}")
            res["result"] = json.loads(res["result_json"]) if res.get("result_json") else None
            return res

    @staticmethod
    def update_battle_state(battle_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        allowed = {
            "status", "player_one_answers", "player_two_answers",
            "player_one_ready", "player_two_ready", "player_one_time", "player_two_time",
            "winner_id", "outcome", "result_json", "started_at", "completed_at"
        }
        fields = []
        values = []
        for k, v in updates.items():
            if k in allowed:
                fields.append(f"{k} = ?")
                if isinstance(v, (dict, list)):
                    values.append(json.dumps(v))
                else:
                    values.append(v)
        if not fields:
            return CompetitionRepository.get_battle_by_id(battle_id)
        values.append(battle_id)
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE battles SET {', '.join(fields)} WHERE id = ?;", tuple(values))
        return CompetitionRepository.get_battle_by_id(battle_id)

    @staticmethod
    def get_user_battles(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM battles
                WHERE player_one_id = ? OR player_two_id = ?
                ORDER BY created_at DESC
                LIMIT ?;
            """, (user_id, user_id, limit))
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["result"] = json.loads(item["result_json"]) if item.get("result_json") else None
                results.append(item)
            return results

    @staticmethod
    def update_battle_stats(user_id: str, is_win: bool, is_tie: bool, xp_delta: int) -> Dict[str, Any]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM battle_stats WHERE user_id = ?;", (user_id,))
            row = cur.fetchone()
            if not row:
                cur.execute("""
                    INSERT INTO battle_stats (user_id, total_battles, wins, losses, ties, win_streak, battle_xp)
                    VALUES (?, 1, ?, ?, ?, ?, ?);
                """, (
                    user_id,
                    1 if is_win else 0,
                    0 if (is_win or is_tie) else 1,
                    1 if is_tie else 0,
                    1 if is_win else 0,
                    xp_delta
                ))
            else:
                s = dict(row)
                tot = s["total_battles"] + 1
                w = s["wins"] + (1 if is_win else 0)
                t = s["ties"] + (1 if is_tie else 0)
                l = s["losses"] + (0 if (is_win or is_tie) else 1)
                streak = (s["win_streak"] + 1) if is_win else 0
                xp = s["battle_xp"] + xp_delta
                cur.execute("""
                    UPDATE battle_stats
                    SET total_battles = ?, wins = ?, losses = ?, ties = ?, win_streak = ?, battle_xp = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?;
                """, (tot, w, l, t, streak, xp, user_id))
        return CompetitionRepository.get_battle_stats(user_id)

    @staticmethod
    def get_battle_stats(user_id: str) -> Dict[str, Any]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM battle_stats WHERE user_id = ?;", (user_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return {
                "user_id": user_id,
                "total_battles": 0,
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "win_streak": 0,
                "battle_xp": 0
            }

    get_user_battle_stats = get_battle_stats

    @staticmethod
    def get_battle_leaderboard(limit: int = 25) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT b.user_id, u.name, b.total_battles, b.wins, b.losses, b.ties, b.win_streak, b.battle_xp
                FROM battle_stats b
                JOIN users u ON b.user_id = u.id
                ORDER BY b.wins DESC, b.battle_xp DESC
                LIMIT ?;
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # C. COLLEGE AND COMPANY HOSTED CHALLENGES
    # =========================================================================

    @staticmethod
    def create_organization(name: str, org_type: str, domain: Optional[str], description: str, created_by: str, is_verified: bool = False) -> Dict[str, Any]:
        init_competition_tables()
        org_id = f"org_{uuid.uuid4().hex[:10]}"
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO organizations (id, name, org_type, domain, description, is_verified, created_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (org_id, name, org_type, domain, description, 1 if is_verified else 0, created_by))
        return CompetitionRepository.get_organization_by_id(org_id)

    @staticmethod
    def get_organization_by_id(org_id: str) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM organizations WHERE id = ?;", (org_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_organizations(verified_only: bool = False) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM organizations"
            if verified_only:
                query += " WHERE is_verified = 1"
            query += " ORDER BY name ASC;"
            cur.execute(query)
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def verify_organization(org_id: str, is_verified: bool = True) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE organizations SET is_verified = ? WHERE id = ?;", (1 if is_verified else 0, org_id))
        return CompetitionRepository.get_organization_by_id(org_id)

    @staticmethod
    def create_hosted_competition(data: Dict[str, Any]) -> Dict[str, Any]:
        init_competition_tables()
        comp_id = f"comp_{uuid.uuid4().hex[:10]}"
        q_json = json.dumps(data["questions"])
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO hosted_competitions (
                    id, org_id, title, description, host_type, subject_id, difficulty,
                    start_time, end_time, eligibility_rules, questions_json, status, created_by_user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                comp_id, data["org_id"], data["title"], data["description"], data["host_type"],
                data["subject_id"], data.get("difficulty", "Intermediate"),
                data["start_time"], data["end_time"], data.get("eligibility_rules", "OPEN"),
                q_json, data.get("status", "SCHEDULED"), data["created_by_user_id"]
            ))
        return CompetitionRepository.get_hosted_competition_by_id(comp_id)

    @staticmethod
    def get_hosted_competition_by_id(comp_id: str) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.*, o.name AS org_name, o.is_verified AS org_is_verified
                FROM hosted_competitions c
                JOIN organizations o ON c.org_id = o.id
                WHERE c.id = ?;
            """, (comp_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["questions"] = json.loads(res["questions_json"])
            return res

    @staticmethod
    def list_hosted_competitions(status: Optional[str] = None, host_type: Optional[str] = None) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            query = """
                SELECT c.*, o.name AS org_name, o.is_verified AS org_is_verified
                FROM hosted_competitions c
                JOIN organizations o ON c.org_id = o.id
                WHERE 1=1
            """
            params = []
            if status:
                query += " AND c.status = ?"
                params.append(status)
            if host_type:
                query += " AND c.host_type = ?"
                params.append(host_type)
            query += " ORDER BY c.start_time DESC;"
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["questions"] = json.loads(item["questions_json"])
                results.append(item)
            return results

    @staticmethod
    def record_competition_submission(comp_id: str, user_id: str, user_name: str, score: int, total_questions: int, time_taken: float) -> Dict[str, Any]:
        init_competition_tables()
        sub_id = f"cpsub_{uuid.uuid4().hex[:10]}"
        percentage = round((score / total_questions * 100), 1) if total_questions > 0 else 0.0
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO competition_submissions (
                    id, competition_id, user_id, user_name, score, total_questions, percentage, time_taken_seconds, submitted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (competition_id, user_id) DO UPDATE SET user_name = excluded.user_name, score = excluded.score,
                    total_questions = excluded.total_questions, percentage = excluded.percentage,
                    time_taken_seconds = excluded.time_taken_seconds, submitted_at = CURRENT_TIMESTAMP;
            """, (sub_id, comp_id, user_id, user_name, score, total_questions, percentage, time_taken))
        return {
            "id": sub_id,
            "competition_id": comp_id,
            "user_id": user_id,
            "user_name": user_name,
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "time_taken_seconds": time_taken
        }

    @staticmethod
    def get_competition_leaderboard(comp_id: str) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, user_name, score, total_questions, percentage, time_taken_seconds, submitted_at
                FROM competition_submissions
                WHERE competition_id = ?
                ORDER BY score DESC, time_taken_seconds ASC;
            """, (comp_id,))
            rows = cur.fetchall()
            ranked = []
            for rank, r in enumerate(rows, start=1):
                item = dict(r)
                item["rank"] = rank
                ranked.append(item)
            return ranked

    # =========================================================================
    # D. UNIFIED GAMIFICATION & XP LEDGER
    # =========================================================================

    @staticmethod
    def record_xp_event(user_id: str, event_key: str, points: int, reason: str, source_type: str, source_id: str) -> bool:
        """Records XP event idempotently. Returns True if awarded, False if already awarded."""
        init_competition_tables()
        eid = f"xpe_{uuid.uuid4().hex[:10]}"
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO xp_ledger (id, event_key, user_id, points_delta, reason, source_type, source_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (event_key) DO NOTHING;
            """, (eid, event_key, user_id, points, reason, source_type, source_id))
            return cur.rowcount > 0

    @staticmethod
    def get_user_total_xp(user_id: str) -> int:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(SUM(points_delta), 0) AS total FROM xp_ledger WHERE user_id = ?;", (user_id,))
            return cur.fetchone()["total"]

    @staticmethod
    def get_user_xp_history(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM xp_ledger WHERE user_id = ? ORDER BY created_at DESC LIMIT ?;", (user_id, limit))
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def get_reward_catalog() -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM reward_catalog WHERE is_active = 1 ORDER BY xp_cost ASC;")
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    @atomic_write
    def redeem_reward(user_id: str, reward_id: str) -> Dict[str, Any]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM reward_catalog WHERE id = ? AND is_active = 1;", (reward_id,))
            reward = cur.fetchone()
            if not reward:
                return {"error": "Reward not found or inactive"}
            if reward["stock"] <= 0:
                return {"error": "Reward is out of stock"}
            cost = reward["xp_cost"]
            cur.execute("SELECT COALESCE(SUM(points_delta), 0) AS total FROM xp_ledger WHERE user_id = ?;", (user_id,))
            cur_xp = cur.fetchone()["total"]
            if cur_xp < cost:
                return {"error": f"Insufficient XP. Requires {cost} XP, you have {cur_xp} XP."}

            cur.execute("UPDATE reward_catalog SET stock=stock-1 WHERE id=? AND stock>0", (reward_id,))

            # Record deduction in ledger
            red_id = f"red_{uuid.uuid4().hex[:10]}"
            event_key = f"redeem.{user_id}.{reward_id}.{red_id}"
            cur.execute("""
                INSERT INTO xp_ledger (id, event_key, user_id, points_delta, reason, source_type, source_id)
                VALUES (?, ?, ?, ?, 'REWARD_REDEMPTION', 'reward_catalog', ?);
            """, (f"xpe_{uuid.uuid4().hex[:10]}", event_key, user_id, -cost, reward_id))

            cur.execute("""
                INSERT INTO reward_redemptions (id, user_id, reward_id, xp_spent)
                VALUES (?, ?, ?, ?);
            """, (red_id, user_id, reward_id, cost))

            return {
                "redemption_id": red_id,
                "reward_title": reward["title"],
                "xp_spent": cost,
                "remaining_xp": cur_xp - cost,
                "status": "CONFIRMED"
            }

    # =========================================================================
    # E. REFERRAL SYSTEM
    # =========================================================================

    @staticmethod
    def get_or_create_user_referral_code(user_id: str, user_name: str) -> str:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT referral_code FROM user_referral_codes WHERE user_id = ?;", (user_id,))
            row = cur.fetchone()
            if row:
                return row["referral_code"]
            # Generate deterministic, clean referral code
            clean_name = "".join(c for c in user_name.upper() if c.isalnum())[:6] or "PRAGYA"
            code = f"PRAGYA-{clean_name}-{user_id[-4:].upper()}"
            cur.execute("INSERT INTO user_referral_codes (user_id, referral_code) VALUES (?, ?) ON CONFLICT (user_id) DO NOTHING;", (user_id, code))
            return code

    @staticmethod
    def get_user_id_by_referral_code(referral_code: str) -> Optional[str]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM user_referral_codes WHERE UPPER(referral_code) = UPPER(?);", (referral_code.strip(),))
            row = cur.fetchone()
            return row["user_id"] if row else None

    @staticmethod
    def record_pending_referral(referrer_id: str, referee_id: str, referral_code: str) -> Dict[str, Any]:
        init_competition_tables()
        if referrer_id == referee_id:
            return {"error": "Self-referral is not permitted"}
        ref_id = f"ref_{uuid.uuid4().hex[:10]}"
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM referrals WHERE referee_id = ?;", (referee_id,))
            if cur.fetchone():
                return {"error": "User already has an active or completed referral"}
            cur.execute("""
                INSERT INTO referrals (id, referrer_id, referee_id, referral_code, status)
                VALUES (?, ?, ?, ?, 'PENDING');
            """, (ref_id, referrer_id, referee_id, referral_code))
        return {"id": ref_id, "referrer_id": referrer_id, "referee_id": referee_id, "status": "PENDING"}

    @staticmethod
    def qualify_referral(referee_id: str, milestone_type: str) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM referrals WHERE referee_id = ? AND status = 'PENDING';", (referee_id,))
            row = cur.fetchone()
            if not row:
                return None
            ref = dict(row)
            # Atomic PENDING -> QUALIFIED: only one concurrent caller can win this transition
            cur.execute("""
                UPDATE referrals
                SET status = 'QUALIFIED', milestone_type = ?, qualified_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'PENDING';
            """, (milestone_type, ref["id"]))
            if cur.rowcount != 1:
                return None
            return dict(ref)

    @staticmethod
    def mark_referral_rewarded(referral_id: str) -> None:
        init_competition_tables()
        with get_db() as conn:
            conn.cursor().execute("UPDATE referrals SET status = 'REWARDED' WHERE id = ? AND status = 'QUALIFIED';", (referral_id,))

    @staticmethod
    def get_user_referrals_summary(user_id: str) -> Dict[str, Any]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT r.*, u.name AS referee_name
                FROM referrals r
                JOIN users u ON r.referee_id = u.id
                WHERE r.referrer_id = ?
                ORDER BY r.created_at DESC;
            """, (user_id,))
            history = [dict(row) for row in cur.fetchall()]
            total_invited = len(history)
            qualified = len([h for h in history if h["status"] in ("QUALIFIED", "REWARDED")])
            pending = total_invited - qualified
            xp_earned = qualified * 150
            return {
                "total_invited": total_invited,
                "pending_referrals": pending,
                "successful_referrals": qualified,
                "xp_earned_from_referrals": xp_earned,
                "referral_history": history
            }

    # =========================================================================
    # F. CERTIFICATES & VERIFICATION
    # =========================================================================

    @staticmethod
    def issue_certificate(user_id: str, user_name: str, cert_type: str, title: str, description: str, metadata: dict) -> Dict[str, Any]:
        init_competition_tables()
        cid = f"cert_{uuid.uuid4().hex[:10]}"
        year = datetime.now().year
        rand_token = uuid.uuid4().hex[:8].upper()
        verif_id = f"PRAGYA-CERT-{year}-{rand_token}"

        from ..services.certificate_signing import signature
        verif_hash = signature({"verification_id":verif_id,"user_id":user_id,"user_name":user_name,
                                "cert_type":cert_type,"title":title,"description":description,
                                "metadata":metadata,"signature_version":2})

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO certificates (
                    id, verification_id, user_id, user_name, cert_type, title, description, metadata_json, verification_hash, signature_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 2);
            """, (cid, verif_id, user_id, user_name, cert_type, title, description, json.dumps(metadata), verif_hash))

        return CompetitionRepository.get_certificate_by_verification_id(verif_id)

    @staticmethod
    def get_certificate_by_verification_id(verif_id: str) -> Optional[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM certificates WHERE verification_id = ?;", (verif_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["metadata"] = json.loads(res["metadata_json"])
            return res

    @staticmethod
    def get_user_certificates(user_id: str) -> List[Dict[str, Any]]:
        init_competition_tables()
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM certificates WHERE user_id = ? ORDER BY issued_at DESC;", (user_id,))
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["metadata"] = json.loads(item["metadata_json"])
                results.append(item)
            return results
