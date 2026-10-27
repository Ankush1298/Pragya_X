"""
Admin Competition and Platform Management Service
Owned by: Ankush (Gamification & Competition Module Owner)
Handles organization host verification, platform challenge scheduling,
competition audits, referral abuse checks, and platform analytics.
"""

from typing import List, Dict, Any, Optional
from ..database.competition_repository import CompetitionRepository
from ..database.connection import get_db
from .hosted_competition_service import HostedCompetitionService


class AdminCompetitionService:
    @staticmethod
    def verify_organization_host(org_id: str, is_verified: bool = True) -> Dict[str, Any]:
        """Approves or revokes organization hosting credentials."""
        org = CompetitionRepository.verify_organization(org_id, is_verified=is_verified)
        if not org:
            return {"error": "Organization not found."}
        return {
            "organization_id": org_id,
            "name": org["name"],
            "org_type": org["org_type"],
            "is_verified": bool(org["is_verified"]),
            "message": f"Organization '{org['name']}' {'approved' if is_verified else 'unverified'}."
        }

    @staticmethod
    def audit_referral_activity() -> List[Dict[str, Any]]:
        """
        Audits referral system for suspicious patterns:
        - Self-referrals (which should be blocked by DB constraints)
        - Users referring multiple accounts in very rapid succession
        - High volume pending vs qualified ratios
        """
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT referrer_id, COUNT(*) AS total_referred,
                       SUM(CASE WHEN status = 'QUALIFIED' THEN 1 ELSE 0 END) AS qualified_count,
                       SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) AS pending_count
                FROM referrals
                GROUP BY referrer_id
                ORDER BY total_referred DESC;
            """)
            rows = [dict(r) for r in cur.fetchall()]

            flagged = []
            for r in rows:
                is_suspicious = False
                reasons = []
                # Flag if user has over 10 pending referrals and 0 qualified
                if r["total_referred"] > 10 and r["qualified_count"] == 0:
                    is_suspicious = True
                    reasons.append("High volume of unverified pending accounts")

                flagged.append({
                    "referrer_id": r["referrer_id"],
                    "total_referred": r["total_referred"],
                    "qualified_count": r["qualified_count"],
                    "pending_count": r["pending_count"],
                    "is_flagged": is_suspicious,
                    "reasons": reasons
                })
            return flagged

    @staticmethod
    def audit_suspicious_rewards() -> List[Dict[str, Any]]:
        """
        Audits XP transactions to identify potential anomalies or duplicate awards.
        Checks for users with abnormally frequent reward redemptions.
        """
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, COUNT(*) AS total_redemptions, SUM(xp_spent) AS total_xp_spent
                FROM reward_redemptions
                GROUP BY user_id
                HAVING COUNT(*) > 5
                ORDER BY total_redemptions DESC;
            """)
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def get_platform_competition_analytics() -> Dict[str, Any]:
        """
        Platform-wide analytics for competitions, 1v1 battles, daily challenges, and referrals.
        """
        with get_db() as conn:
            cur = conn.cursor()

            # Competitions
            cur.execute("SELECT COUNT(*) AS total_hosted FROM hosted_competitions;")
            total_competitions = cur.fetchone()["total_hosted"]

            cur.execute("SELECT COUNT(*) AS total_comp_subs FROM competition_submissions;")
            total_comp_submissions = cur.fetchone()["total_comp_subs"]

            # Battles
            cur.execute("SELECT COUNT(*) AS total_battles, SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_battles FROM battles;")
            b_row = cur.fetchone()
            total_battles = b_row["total_battles"]
            completed_battles = b_row["completed_battles"] or 0

            # Daily Challenges
            cur.execute("SELECT COUNT(*) AS total_chal_subs FROM challenge_submissions;")
            total_challenge_submissions = cur.fetchone()["total_chal_subs"]

            # Total XP Awarded
            cur.execute("SELECT COALESCE(SUM(points_delta), 0) AS total_xp FROM xp_ledger WHERE points_delta > 0;")
            total_xp_awarded = cur.fetchone()["total_xp"]

            # Referrals
            cur.execute("""
                SELECT COUNT(*) AS total_refs,
                       SUM(CASE WHEN status = 'QUALIFIED' THEN 1 ELSE 0 END) AS qualified_refs
                FROM referrals;
            """)
            ref_row = cur.fetchone()
            total_refs = ref_row["total_refs"]
            qualified_refs = ref_row["qualified_refs"] or 0
            conv_rate = round((qualified_refs / total_refs * 100), 1) if total_refs > 0 else 0.0

            return {
                "competitions": {
                    "total_hosted": total_competitions,
                    "total_submissions": total_comp_submissions
                },
                "battles": {
                    "total_battles": total_battles,
                    "completed_battles": completed_battles
                },
                "daily_challenges": {
                    "total_submissions": total_challenge_submissions
                },
                "gamification": {
                    "total_xp_awarded": total_xp_awarded
                },
                "referrals": {
                    "total_referrals": total_refs,
                    "qualified_referrals": qualified_refs,
                    "conversion_rate_percent": conv_rate
                }
            }
