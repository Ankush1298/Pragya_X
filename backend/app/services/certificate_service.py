"""
Certificates and Shareable Achievements Service
Owned by: Ankush (Gamification & Competition Module Owner)
Generates tamper-evident cryptographic verification hashes, public verification responses,
and shareable social preview achievement cards.
"""

import hashlib
import json
from datetime import datetime, timezone
import html as _html
from ..config import settings
from typing import List, Dict, Any, Optional
from ..database.competition_repository import CompetitionRepository
from ..database.connection import atomic_write


class CertificateService:
    @staticmethod
    @atomic_write
    def issue_certificate(
        user_id: str,
        user_name: str,
        cert_type: str,
        title: str,
        description: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Issues an authentic certificate for verified accomplishments.
        Prevents duplicate certificates for the same event via metadata check.
        """
        valid_types = {"ASSESSMENT", "BATTLE_WINNER", "COMPETITION_WINNER", "TRACK_COMPLETION", "REFERRAL_AMBASSADOR"}
        clean_type = cert_type.strip().upper()
        if clean_type not in valid_types:
            clean_type = "ASSESSMENT"

        # Check existing user certs to prevent duplicates for same event
        existing = CompetitionRepository.get_user_certificates(user_id)
        for c in existing:
            meta = c.get("metadata", {})
            if meta.get("competition_id") and meta.get("competition_id") == metadata.get("competition_id"):
                return c
            if meta.get("battle_id") and meta.get("battle_id") == metadata.get("battle_id"):
                return c
            if meta.get("assessment_id") and meta.get("assessment_id") == metadata.get("assessment_id"):
                return c

        return CompetitionRepository.issue_certificate(
            user_id=user_id,
            user_name=user_name,
            cert_type=clean_type,
            title=title,
            description=description,
            metadata=metadata
        )

    @staticmethod
    def verify_certificate(verification_id: str) -> Dict[str, Any]:
        """
        Authoritative public verification endpoint.
        Recomputes SHA256 checksum to ensure the certificate was not forged or tampered with.
        """
        clean_id = verification_id.strip().upper()
        cert = CompetitionRepository.get_certificate_by_verification_id(clean_id)
        if not cert:
            return {
                "is_valid": False,
                "error": f"Certificate with ID '{verification_id}' does not exist or has been revoked."
            }

        # Validate cryptographic integrity with authenticated digital signature (HMAC-SHA256)
        import hmac
        from ..config import settings

        from .certificate_signing import signature
        is_valid_signature = hmac.compare_digest(cert["verification_hash"], signature(cert))

        if not is_valid_signature:
            return {
                "is_valid": False,
                "error": "Tamper alert: Certificate cryptographic signature mismatch."
            }

        return {
            "is_valid": True,
            "verification_id": cert["verification_id"],
            "recipient_name": cert["user_name"],
            "cert_type": cert["cert_type"],
            "title": cert["title"],
            "description": cert["description"],
            "metadata": cert["metadata"],
            "issued_at": cert["issued_at"],
            "issuer": "PragyaX",
            "verification_hash": cert["verification_hash"]
        }

    @staticmethod
    def get_user_certificates(user_id: str) -> List[Dict[str, Any]]:
        """Returns all certificates awarded to a student."""
        return CompetitionRepository.get_user_certificates(user_id)

    @staticmethod
    def get_shareable_card_data(verification_id: str) -> Dict[str, Any]:
        """
        Produces rich preview metadata and visual card data for LinkedIn / Twitter / portfolio sharing.
        """
        verif = CertificateService.verify_certificate(verification_id)
        if not verif["is_valid"]:
            return {"error": verif.get("error")}
        base = settings.PUBLIC_BASE_URL

        return {
            "title": f"PragyaX Challenge Achievement — {verif['title']}",
            "recipient": verif["recipient_name"],
            "verification_url": f"{base}/#/verify/{verif['verification_id']}",
            "badge_icon": "trophy" if "WINNER" in verif["cert_type"] else "award",
            "accent_color": "#4F46E5",
            "share_text": f"Proud to have earned the '{verif['title']}' achievement on PragyaX! Verify here: {base}/#/verify/{verif['verification_id']}",
            "certificate": verif
        }

    @staticmethod
    def render_downloadable_certificate_html(verification_id: str) -> Dict[str, Any]:
        """
        Renders a printable/downloadable HTML certificate view with styling,
        signatures, and verification QR/link.
        """
        verif = CertificateService.verify_certificate(verification_id)
        if not verif["is_valid"]:
            return {"error": verif.get("error")}

        esc = lambda v: _html.escape(str(v or ""))
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>PragyaX Achievement - {esc(verif['verification_id'])}</title>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #f3f4f6; margin: 0; padding: 40px; display: flex; justify-content: center; }}
  .cert-container {{ background: #fff; width: 800px; padding: 50px; border: 12px solid #4F46E5; box-shadow: 0 10px 25px rgba(0,0,0,0.1); text-align: center; border-radius: 8px; position: relative; }}
  .header {{ font-size: 32px; font-weight: bold; color: #1e1b4b; letter-spacing: 2px; text-transform: uppercase; }}
  .subtitle {{ font-size: 14px; color: #6b7280; margin-top: 5px; text-transform: uppercase; letter-spacing: 1px; }}
  .presents {{ font-size: 18px; color: #374151; margin: 30px 0 10px; font-style: italic; }}
  .name {{ font-size: 36px; font-weight: 800; color: #4F46E5; text-decoration: underline; margin-bottom: 20px; }}
  .desc {{ font-size: 16px; color: #4b5563; line-height: 1.6; max-width: 600px; margin: 0 auto 30px; }}
  .title-tag {{ font-size: 22px; font-weight: bold; color: #111827; margin-bottom: 10px; }}
  .footer {{ margin-top: 40px; border-top: 1px solid #e5e7eb; padding-top: 20px; display: flex; justify-content: space-between; font-size: 12px; color: #9ca3af; }}
  .badge {{ background: #eef2ff; color: #4F46E5; padding: 6px 16px; border-radius: 9999px; font-weight: bold; display: inline-block; margin-bottom: 20px; }}
</style>
</head>
<body>
<div class="cert-container">
  <div class="header">PragyaX</div>
  <div class="subtitle">PragyaX Challenge Achievement</div>
  <div class="presents">This certifies that</div>
  <div class="name">{esc(verif['recipient_name'])}</div>
  <div class="badge">{esc(verif['cert_type'])}</div>
  <div class="title-tag">{esc(verif['title'])}</div>
  <div class="desc">{esc(verif['description'])}</div>
  <div class="footer">
    <div>Verification ID: <strong>{esc(verif['verification_id'])}</strong></div>
    <div>Issued: {verif['issued_at'][:10] if verif.get('issued_at') else '2026'}</div>
    <div>Platform achievement record - not an accredited qualification</div>
  </div>
</div>
</body>
</html>"""
        return {"html": html, "verification_id": verif["verification_id"]}
