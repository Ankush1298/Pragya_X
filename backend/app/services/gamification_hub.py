"""
Unified Gamification Hub
Owned by: Ankush (Gamification & Competition Module Owner)
Reuses: points_ledger_domain.py, gamification_service.py, leaderboard_engine.py
Unifies XP calculation, level progression, badges, streaks, and reward store redemption.
"""

from typing import List, Dict, Any, Optional
from ..database.competition_repository import CompetitionRepository
from ..database.repository import Repository

LEVEL_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 250,
    4: 500,
    5: 1000,
    6: 2000,
    7: 4000
}


def compute_level(xp: int) -> int:
    current = 1
    for lvl, thresh in sorted(LEVEL_THRESHOLDS.items()):
        if xp >= thresh:
            current = lvl
    return current


class GamificationHub:
    LEVEL_TITLES = {
        1: "Novice Coder",
        2: "Syntax Apprentice",
        3: "Logic Practitioner",
        4: "Algorithm Specialist",
        5: "Systems Expert",
        6: "Architecture Master",
        7: "Pragya Grandmaster"
    }

    @staticmethod
    def get_user_profile_gamification(user_id: str) -> Dict[str, Any]:
        """
        Retrieves unified gamification profile:
        Total XP, current level, next level threshold, progress percentage, badges, streaks.
        """
        total_xp = CompetitionRepository.get_user_total_xp(user_id)
        current_streak = CompetitionRepository.get_user_streak(user_id)
        battle_stats = CompetitionRepository.get_user_battle_stats(user_id)

        # Level determination
        level = compute_level(total_xp)
        title = GamificationHub.LEVEL_TITLES.get(level, "Master")

        # Thresholds
        next_level = level + 1
        current_threshold = LEVEL_THRESHOLDS.get(level, 0)
        next_threshold = LEVEL_THRESHOLDS.get(next_level, current_threshold + 1000)

        xp_in_level = max(0, total_xp - current_threshold)
        span = max(1, next_threshold - current_threshold)
        progress_pct = min(100.0, round((xp_in_level / span) * 100, 1))

        # Dynamic Earned Badges
        badges = []
        if total_xp >= 50:
            badges.append({"id": "first_xp", "name": "First Sparks", "icon": "zap", "desc": "Earned first 50 XP"})
        if current_streak.get("current_streak", 0) >= 3:
            badges.append({"id": "streak_3", "name": "Consistent Scholar", "icon": "flame", "desc": "3-day daily streak"})
        if current_streak.get("current_streak", 0) >= 7:
            badges.append({"id": "streak_7", "name": "Unstoppable", "icon": "fire", "desc": "7-day daily streak"})
        if battle_stats.get("wins", 0) >= 1:
            badges.append({"id": "battle_first_blood", "name": "First Blood", "icon": "swords", "desc": "Won first 1v1 battle"})
        if battle_stats.get("wins", 0) >= 5:
            badges.append({"id": "battle_veteran", "name": "Battle Veteran", "icon": "shield", "desc": "Won 5 1v1 battles"})
        if total_xp >= 1000:
            badges.append({"id": "xp_millennium", "name": "Century Scholar", "icon": "award", "desc": "Crossed 1000 XP mark"})

        return {
            "user_id": user_id,
            "total_xp": total_xp,
            "level": level,
            "title": title,
            "current_threshold": current_threshold,
            "next_threshold": next_threshold,
            "progress_percentage": progress_pct,
            "streak": current_streak,
            "battle_stats": battle_stats,
            "badges": badges
        }

    @staticmethod
    def get_xp_history(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the user's transparent XP transaction history."""
        return CompetitionRepository.get_user_xp_history(user_id, limit=limit)

    @staticmethod
    def get_reward_catalog_with_eligibility(user_id: str) -> List[Dict[str, Any]]:
        """
        Returns all rewards in catalog annotated with can_afford flag based on user's current XP.
        """
        total_xp = CompetitionRepository.get_user_total_xp(user_id)
        catalog = CompetitionRepository.get_reward_catalog()
        for item in catalog:
            item["can_afford"] = (total_xp >= item["xp_cost"])
            item["shortfall"] = max(0, item["xp_cost"] - total_xp)
            # No fulfilment pipeline exists: every reward is a demo entry and must be presented as such.
            item["is_demo"] = True
            item["fulfillment_note"] = "Demo reward: redeeming deducts demo XP only. Nothing is shipped or scheduled."
        return catalog

    @staticmethod
    def redeem_reward(user_id: str, reward_id: str) -> Dict[str, Any]:
        """Redeems a reward from the catalog, deducting XP in the ledger."""
        return CompetitionRepository.redeem_reward(user_id, reward_id)
