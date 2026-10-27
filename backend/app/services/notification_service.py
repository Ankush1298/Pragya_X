"""
In-app notifications. Stored per user, de-duplicated by (user, dedupe_key), filtered by the user's preferences.
No push/email infrastructure: honest, reliable in-app only.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from ..database.learning_repository import LearningRepository
from ..database.connection import get_db

# notification kind -> preference flag
_KIND_PREF = {
    "battle": "battles", "achievement": "achievements", "reminder": "reminders",
    "revision": "reminders", "project": "projects", "system": None,
}


def _in_quiet_hours(prefs: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    start, end = prefs.get("quiet_start"), prefs.get("quiet_end")
    if not start or not end:
        return False
    cur = (now or datetime.now()).strftime("%H:%M")
    return (start <= cur < end) if start <= end else (cur >= start or cur < end)


def notify(user_id: str, kind: str, title: str, body: str = "", link: Optional[str] = None,
           dedupe_key: Optional[str] = None) -> bool:
    """Create a notification unless opted out / (for reminders) inside quiet hours. Never raises."""
    try:
        with get_db() as conn, conn.transaction():
            prefs = LearningRepository.get_prefs(user_id)
            flag = _KIND_PREF.get(kind)
            if flag and not prefs.get(flag, 1):
                return False
            if kind in ("reminder", "revision") and _in_quiet_hours(prefs):
                return False
            return LearningRepository.add_notification(
                user_id, kind, title, body, link, dedupe_key or f"{kind}:{title}:{body}")
    except Exception:  # a notification must never break the action that triggered it
        import logging
        logging.getLogger(__name__).warning("Optional in-app notification could not be saved")
        return False


def valid_hhmm(v: Optional[str]) -> bool:
    if v in (None, ""):
        return True
    try:
        datetime.strptime(v, "%H:%M")
        return True
    except ValueError:
        return False
