"""Canonical, versioned HMAC payloads for platform achievement records."""
import hashlib
import hmac
import json
from ..config import settings


def signature(cert):
    if cert.get('signature_version',1)==1:
        payload=f"{cert['verification_id']}:{cert['user_id']}:{cert['cert_type']}:{cert['title']}".encode()
    else:
        payload=json.dumps({k:cert[k] for k in ('verification_id','user_id','user_name','cert_type','title','description','metadata')},
                           sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    return hmac.new(settings.SECRET_KEY.encode(),payload,hashlib.sha256).hexdigest()
