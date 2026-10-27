"""
PragyaX Routers Package
"""

from .health import router as health_router
from .auth import router as auth_router
from .subjects import router as subjects_router
from .chat import router as chat_router
from .assessments import router as assessments_router
from .dashboard import router as dashboard_router
from .challenges import router as challenges_router
from .roadmap import router as roadmap_router
from .battles import router as battles_router
from .competitions import router as competitions_router
from .referrals import router as referrals_router
from .certificates import router as certificates_router
from .gamification import router as gamification_router
from .admin_competitions import router as admin_competitions_router
from .learning import router as learning_router
from .notifications import router as notifications_router

__all__ = [
    "health_router",
    "auth_router",
    "subjects_router",
    "chat_router",
    "assessments_router",
    "dashboard_router",
    "challenges_router",
    "roadmap_router",
    "battles_router",
    "competitions_router",
    "referrals_router",
    "certificates_router",
    "gamification_router",
    "admin_competitions_router",
    "learning_router",
    "notifications_router",
]
