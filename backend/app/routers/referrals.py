"""
Referral System Router
Owned by: Ankush (Gamification & Competition Module Owner)
Handles referral code distribution, entry validation, and tracking dashboard.
"""

from ..config import settings
from fastapi import APIRouter, Depends, HTTPException, status
from ..services.auth_service import get_current_user
from ..services.referral_service import ReferralService
from ..schemas.referrals import ReferralApplyRequest, ReferralDashboardResponse

router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.get("/my-code")
def get_my_referral_code(user: dict = Depends(get_current_user)):
    """Retrieves unique referral code and invite link for current student."""
    code = ReferralService.get_or_generate_code(user["id"], user["name"])
    return {
        "referral_code": code,
        "share_url": f"{settings.PUBLIC_BASE_URL}/#/register?ref={code}"
    }


@router.post("/apply")
def apply_referral_code(payload: ReferralApplyRequest, user: dict = Depends(get_current_user)):
    """
    Applies referral code during onboarding.
    Validates anti-abuse rules (no self-referral, one referrer per user).
    Referral is pending until a real learning milestone is completed.
    """
    result = ReferralService.apply_referral_code(
        referee_id=user["id"],
        code=payload.referral_code
    )
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


@router.get("/dashboard")
def get_referral_dashboard(user: dict = Depends(get_current_user)):
    """Returns referral stats and transaction history for the logged-in student."""
    return ReferralService.get_referral_dashboard(user["id"], user["name"])
