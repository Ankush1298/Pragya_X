from ..database.connection import atomic_write
"""
Referral System Service
Owned by: Ankush (Gamification & Competition Module Owner)
Handles referral code generation, entry, anti-abuse checks, pending status,
and reward qualification after genuine learning activities.
"""

from typing import List, Dict, Any, Optional
from ..database.competition_repository import CompetitionRepository
from ..config import settings
from ..database.learning_repository import LearningRepository
from ..database.repository import Repository

REFERRER_XP = 150
REFEREE_XP = 50
QUALIFY_RULE = ("Qualifies when the invited student completes their first diagnostic assessment AND their first "
                "learning module (practice passed). Rewards: %d XP for you, %d XP welcome bonus for them, granted once." % (REFERRER_XP, REFEREE_XP))


class ReferralService:
    @staticmethod
    def get_or_generate_code(user_id: str, user_name: str) -> str:
        """Retrieves or creates unique, clean user referral code."""
        return CompetitionRepository.get_or_create_user_referral_code(user_id, user_name)

    @staticmethod
    @atomic_write
    def apply_referral_code(referee_id: str, code: str) -> Dict[str, Any]:
        """
        Applies a referral code during registration or onboarding.
        Enforces anti-abuse rules:
        - Code must exist and be valid
        - No self-referral
        - Only one qualifying referrer per student
        - Referral is placed in PENDING state; NO REWARD is given immediately!
        """
        clean_code = code.strip().upper()
        if not clean_code:
            return {"error": "Referral code cannot be empty."}

        referrer_id = CompetitionRepository.get_user_id_by_referral_code(clean_code)
        if not referrer_id:
            return {"error": "Invalid referral code. No matching user found."}

        if referrer_id == referee_id:
            return {"error": "Self-referral is not allowed. You cannot use your own referral code."}

        if LearningRepository.user_has_completed_mission(referee_id):
            return {"error": "Referral codes can only be applied before your first learning mission."}

        result = CompetitionRepository.record_pending_referral(
            referrer_id=referrer_id,
            referee_id=referee_id,
            referral_code=clean_code
        )

        if "error" in result:
            return result

        return {
            "status": "PENDING",
            "message": "Referral code applied! " + QUALIFY_RULE,
            "referral": result
        }

    @staticmethod
    @atomic_write
    def check_and_qualify_referral(referee_id: str, milestone_type: str) -> Optional[Dict[str, Any]]:
        """
        Called when a student completes a qualifying learning activity
        (e.g., completes first assessment with passing grade, or completes first daily challenge).
        Transitions referral from PENDING -> QUALIFIED and issues XP rewards server-side.
        """
        # Product rule: BOTH the initial assessment and the first learning mission are required.
        if not (LearningRepository.user_has_diagnostic(referee_id) and LearningRepository.user_has_completed_mission(referee_id)):
            return None
        referral = CompetitionRepository.qualify_referral(referee_id, milestone_type)
        if not referral:
            return None  # No pending referral found for this user

        referrer_id = referral["referrer_id"]
        ref_id = referral["id"]

        # Award Referrer: 150 XP (Idempotent)
        CompetitionRepository.record_xp_event(
            user_id=referrer_id,
            event_key=f"referral.referrer.{ref_id}",
            points=REFERRER_XP,
            reason=f"Invited friend completed {milestone_type}",
            source_type="referral",
            source_id=ref_id
        )

        # Award Referee: 50 XP Welcome bonus (Idempotent)
        CompetitionRepository.record_xp_event(
            user_id=referee_id,
            event_key=f"referral.referee.{ref_id}",
            points=REFEREE_XP,
            reason=f"Welcome bonus for completing {milestone_type} via referral",
            source_type="referral",
            source_id=ref_id
        )

        CompetitionRepository.mark_referral_rewarded(ref_id)
        return {
            "referral_id": ref_id,
            "status": "REWARDED",
            "referrer_id": referrer_id,
            "referee_id": referee_id,
            "referrer_points": REFERRER_XP,
            "referee_points": REFEREE_XP,
            "milestone_type": milestone_type
        }

    @staticmethod
    def get_referral_dashboard(user_id: str, user_name: str) -> Dict[str, Any]:
        """
        Returns referrer's code, referral link, total invited, pending, successful,
        and full referral history.
        """
        code = ReferralService.get_or_generate_code(user_id, user_name)
        summary = CompetitionRepository.get_user_referrals_summary(user_id)

        return {
            "referral_code": code,
            "share_url": f"{settings.PUBLIC_BASE_URL}/#/register?ref={code}",
            "total_invited": summary["total_invited"],
            "pending_referrals": summary["pending_referrals"],
            "successful_referrals": summary["successful_referrals"],
            "xp_earned_from_referrals": summary["xp_earned_from_referrals"],
            "referral_history": summary["referral_history"],
            "reward_rule": QUALIFY_RULE,
            "referrer_xp": REFERRER_XP,
            "referee_xp": REFEREE_XP,
        }
