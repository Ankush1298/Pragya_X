from ..database.connection import atomic_write, get_db
"""
Hosted Competition Service (College & Company Challenges)
Owned by: Ankush (Gamification & Competition Module Owner)
Supports: PLATFORM, STUDENT, COLLEGE, COMPANY hosted competitions.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from ..database.competition_repository import CompetitionRepository
from ..database.repository import Repository
from .certificate_service import CertificateService
from .notification_service import notify


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def effective_status(comp: Dict[str, Any]) -> str:
    """Stored status wins for terminal states; otherwise derive SCHEDULED/ACTIVE/CLOSED from the time window."""
    stored = (comp.get("status") or "SCHEDULED").upper()
    if stored in ("COMPLETED", "ARCHIVED", "CANCELLED", "DRAFT"):
        return stored
    start, end, now = _parse_dt(comp.get("start_time")), _parse_dt(comp.get("end_time")), _now()
    if start and now < start:
        return "SCHEDULED"
    if end and now > end:
        return "CLOSED"
    return "ACTIVE"


class HostedCompetitionService:
    @staticmethod
    def register_organization(
        name: str,
        org_type: str,
        domain: Optional[str],
        description: str,
        created_by_user_id: str
    ) -> Dict[str, Any]:
        """
        Registers a new host organization.
        COLLEGE and COMPANY organizations require administrative verification before
        official host credentials can be published.
        """
        valid_types = {"PLATFORM", "STUDENT", "COLLEGE", "COMPANY"}
        clean_type = org_type.strip().upper()
        if clean_type not in valid_types:
            return {"error": f"Invalid org_type. Must be one of: {', '.join(sorted(valid_types))}"}

        # STUDENT organizations are auto-verified as student clubs;
        # COLLEGE and COMPANY require admin approval.
        auto_verified = (clean_type == "STUDENT")

        org = CompetitionRepository.create_organization(
            name=name.strip(),
            org_type=clean_type,
            domain=domain.strip() if domain else None,
            description=description.strip(),
            created_by=created_by_user_id,
            is_verified=auto_verified
        )
        return {"organization": org}

    @staticmethod
    def list_organizations(verified_only: bool = False) -> List[Dict[str, Any]]:
        """Lists registered organizations, optionally filtered by verification status."""
        return CompetitionRepository.list_organizations(verified_only=verified_only)

    @staticmethod
    def get_organization(org_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves organization details."""
        return CompetitionRepository.get_organization_by_id(org_id)

    @staticmethod
    def create_competition(
        user_id: str,
        org_id: str,
        title: str,
        description: str,
        subject_id: str,
        difficulty: str,
        start_time: str,
        end_time: str,
        questions: List[Dict[str, Any]],
        eligibility_rules: str = "OPEN",
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Creates and schedules a hosted challenge.
        Enforces organization verification: only verified organizations or admins can host official challenges.
        """
        org = CompetitionRepository.get_organization_by_id(org_id)
        if not org:
            return {"error": "Organization not found."}

        # Only the creator or an admin can create challenges for this org
        if org["created_by_user_id"] != user_id and not is_admin:
            return {"error": "Unauthorized: You are not authorized to create challenges for this organization."}

        # Only verified organizations or platform admins can host COLLEGE / COMPANY / PLATFORM challenges
        host_type = org["org_type"]
        if host_type in ("COLLEGE", "COMPANY", "PLATFORM") and not org["is_verified"] and not is_admin:
            return {
                "error": f"Organization '{org['name']}' is pending administrative verification. "
                         f"Official {host_type} challenges cannot be hosted until verified."
            }

        start_dt,end_dt=_parse_dt(start_time),_parse_dt(end_time)
        if not start_dt or not end_dt or end_dt <= start_dt:
            return {"error":"Provide valid start and end times; the end must be after the start."}
        if not title.strip() or not description.strip():
            return {"error":"A title and description are required."}
        if any(q.get("correct_option", "").strip().upper() not in {"A","B","C","D"} for q in questions):
            return {"error":"Each question must have a valid correct option A-D."}
        if not questions:
            return {"error": "Competition must contain at least one question."}

        # Validate questions schema
        sanitized_questions = []
        for i, q in enumerate(questions):
            if not all(k in q for k in ("question_text", "option_a", "option_b", "option_c", "option_d", "correct_option")):
                return {"error": f"Question {i+1} is missing required fields."}
            sanitized_questions.append({
                "id": q.get("id") or f"cq_{i+1}",
                "question_text": q["question_text"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
                "correct_option": q["correct_option"].strip().upper(),
                "explanation": q.get("explanation", ""),
                "topic": q.get("topic", "General")
            })

        comp_data = {
            "org_id": org_id,
            "title": title.strip(),
            "description": description.strip(),
            "host_type": host_type,
            "subject_id": subject_id,
            "difficulty": difficulty,
            "start_time": start_time,
            "end_time": end_time,
            "eligibility_rules": eligibility_rules,
            "questions": sanitized_questions,
            "status": "ACTIVE",
            "created_by_user_id": user_id
        }

        comp = CompetitionRepository.create_hosted_competition(comp_data)
        return {"competition": comp}

    @staticmethod
    def list_competitions(status: Optional[str] = None, host_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists hosted competitions, hiding answer keys from questions."""
        comps = CompetitionRepository.list_hosted_competitions(status=status, host_type=host_type)
        # Strip authoritative answer keys from public listing
        for c in comps:
            c["status"] = effective_status(c)
            safe_q = []
            for q in c.get("questions", []):
                safe_q.append({
                    "id": q["id"],
                    "question_text": q["question_text"],
                    "option_a": q["option_a"],
                    "option_b": q["option_b"],
                    "option_c": q["option_c"],
                    "option_d": q["option_d"],
                    "topic": q.get("topic", "")
                })
            c.pop("questions_json",None)
            c["questions"] = [] if c["status"] == "SCHEDULED" else safe_q
        return comps

    @staticmethod
    def get_competition_for_student(comp_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves a competition without answers, including user submission if present."""
        comp = CompetitionRepository.get_hosted_competition_by_id(comp_id)
        if not comp:
            return None
        comp["status"] = effective_status(comp)

        safe_q = []
        for q in comp.get("questions", []):
            safe_q.append({
                "id": q["id"],
                "question_text": q["question_text"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
                "topic": q.get("topic", "")
            })
        comp.pop("questions_json",None)
        comp["questions"] = [] if comp["status"] == "SCHEDULED" else safe_q  # no peeking before the start

        user_sub = None
        if user_id:
            leaderboard = CompetitionRepository.get_competition_leaderboard(comp_id)
            for entry in leaderboard:
                if entry["user_id"] == user_id:
                    user_sub = entry
                    break
        comp["user_submission"] = user_sub
        if user_id and comp["status"] in ("SCHEDULED","ACTIVE"):
            comp["registration"] = HostedCompetitionService.register_participant(comp_id,user_id,start=comp["status"]=="ACTIVE")

        return comp

    @staticmethod
    @atomic_write
    def submit_competition(
        comp_id: str,
        user_id: str,
        user_name: str,
        answers: Dict[str, str],
        time_taken_seconds: float
    ) -> Dict[str, Any]:
        """
        Grades participant's competition answers against server-held answer keys.
        Calculates score, percentage, awards XP once, and updates leaderboard.
        """
        comp = CompetitionRepository.get_hosted_competition_by_id(comp_id)
        if not comp:
            return {"error": "Competition not found."}

        status_now = effective_status(comp)
        if status_now == "SCHEDULED":
            return {"error": "This competition has not started yet."}
        if status_now != "ACTIVE":
            return {"error": f"Competition is {status_now.lower()}, submissions are closed."}
        if any(e["user_id"] == user_id for e in CompetitionRepository.get_competition_leaderboard(comp_id)):
            return {"error": "You have already submitted to this competition. One attempt per student."}

        registration=HostedCompetitionService.register_participant(comp_id,user_id,start=True)
        started=_parse_dt(registration.get("started_at"))
        time_taken_seconds=max(0.0,(_now()-started).total_seconds()) if started else 0.0
        valid_ids={q["id"] for q in comp["questions"]}
        if set(answers)-valid_ids or any(v.strip().upper() not in {"A","B","C","D"} for v in answers.values()):
            return {"error":"Answer sheet contains invalid questions or choices."}

        # Grade authoritatively
        raw_questions = comp["questions"]
        correct_count = 0
        total_questions = len(raw_questions)

        for q in raw_questions:
            q_id = q["id"]
            user_choice = answers.get(q_id, "").strip().upper()
            if user_choice == q["correct_option"].strip().upper():
                correct_count += 1

        submission = CompetitionRepository.record_competition_submission(
            comp_id=comp_id,
            user_id=user_id,
            user_name=user_name,
            score=correct_count,
            total_questions=total_questions,
            time_taken=time_taken_seconds
        )

        # Award XP idempotently (100 XP + 50 bonus for perfect score)
        base_xp = 100
        if correct_count == total_questions and total_questions > 0:
            base_xp += 50
        CompetitionRepository.record_xp_event(
            user_id=user_id,
            event_key=f"comp.{comp_id}.{user_id}",
            points=base_xp,
            reason=f"Completed {comp['title']} ({comp['host_type']})",
            source_type="competition",
            source_id=comp_id
        )

        return {
            "submission": submission,
            "score": correct_count,
            "total_questions": total_questions,
            "percentage": submission["percentage"],
            "xp_awarded": base_xp
        }

    @staticmethod
    def get_competition_leaderboard(comp_id: str) -> List[Dict[str, Any]]:
        """Retrieves official ranked leaderboard for a hosted competition."""
        return CompetitionRepository.get_competition_leaderboard(comp_id)

    @staticmethod
    def get_organizer_dashboard(comp_id: str, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Returns full analytics and result dashboard for the challenge organizer or admin.
        """
        comp = CompetitionRepository.get_hosted_competition_by_id(comp_id)
        if not comp:
            return {"error": "Competition not found."}

        if comp["created_by_user_id"] != user_id and not is_admin:
            return {"error": "Unauthorized: Only the host organizer or admin can view this dashboard."}

        leaderboard = CompetitionRepository.get_competition_leaderboard(comp_id)
        total_participants = len(leaderboard)
        avg_score = round(sum(e["score"] for e in leaderboard) / total_participants, 2) if total_participants > 0 else 0.0
        avg_percentage = round(sum(e["percentage"] for e in leaderboard) / total_participants, 1) if total_participants > 0 else 0.0

        top_3 = leaderboard[:3]

        return {
            "competition": {
                "id": comp["id"],
                "title": comp["title"],
                "org_name": comp.get("org_name"),
                "host_type": comp["host_type"],
                "status": comp["status"],
                "start_time": comp["start_time"],
                "end_time": comp["end_time"]
            },
            "analytics": {
                "total_participants": total_participants,
                "average_score": avg_score,
                "average_percentage": avg_percentage,
                "winners": top_3
            },
            "full_leaderboard": leaderboard
        }

    @staticmethod
    @atomic_write
    def announce_winners_and_issue_certificates(comp_id: str, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Announces winners and automatically issues verified competition certificates
        to top performers (Rank 1 champion).
        """
        comp = CompetitionRepository.get_hosted_competition_by_id(comp_id)
        if not comp:
            return {"error": "Competition not found."}

        if comp["created_by_user_id"] != user_id and not is_admin:
            return {"error": "Unauthorized: Only the host organizer or admin can announce winners."}

        leaderboard = CompetitionRepository.get_competition_leaderboard(comp_id)
        if not leaderboard:
            return {"error": "Cannot announce winners: No participants yet."}

        winner = leaderboard[0]
        # Issue winner certificate
        cert = CertificateService.issue_certificate(
            user_id=winner["user_id"],
            user_name=winner["user_name"],
            cert_type="COMPETITION_WINNER",
            title=f"Champion: {comp['title']}",
            description=f"First Place in {comp.get('org_name', 'Hosted')} {comp['title']} Competition",
            metadata={
                "competition_id": comp_id,
                "rank": 1,
                "score": winner["score"],
                "total_questions": winner["total_questions"],
                "org_name": comp.get("org_name")
            }
        )

        notify(
            winner["user_id"],
            "achievement",
            "Competition Winner!",
            f"You won {comp['title']}! Your verified certificate is ready.",
            f"/certificates/{cert['verification_id']}",
            f"cert:{cert['verification_id']}"
        )

        with get_db() as conn:
            conn.cursor().execute("UPDATE hosted_competitions SET status='COMPLETED' WHERE id=?",(comp_id,))

        return {
            "winner": winner,
            "certificate": cert,
            "top_3": leaderboard[:3],
            "status": "ANNOUNCED"
        }


    @staticmethod
    @atomic_write
    def register_participant(comp_id,user_id,start=False):
        with get_db() as conn:
            cur=conn.cursor()
            cur.execute("INSERT INTO competition_registrations(comp_id,user_id,started_at) "
                        "VALUES (?,?,CASE WHEN ? THEN now() ELSE NULL END) "
                        "ON CONFLICT(comp_id,user_id) DO UPDATE SET started_at=COALESCE(competition_registrations.started_at,excluded.started_at) RETURNING *",
                        (comp_id,user_id,start))
            return cur.fetchone()
