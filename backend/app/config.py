"""
PragyaX Backend Configuration
Owned by: Arsh (FastAPI Backend Architecture)
"""

import os
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def _load_dotenv(path: str) -> None:
    """Minimal .env loader (stdlib only). Real environment variables win."""
    if not os.path.exists(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(os.path.join(ROOT_DIR, ".env"))


def sanitize_db_url(url: Optional[str]) -> str:
    """Masks credentials in a database URL for safe logging and error reporting."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = f"{parsed.username or ''}:***@{parsed.hostname or ''}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse(parsed._replace(netloc=netloc))
        return url
    except Exception:
        return "[sanitized-database-url]"


def validate_postgres_url(url: str) -> str:
    """Validates PostgreSQL URL format without exposing credentials in errors."""
    trimmed = url.strip()
    if not trimmed:
        return ""
    if not (trimmed.startswith("postgresql://") or trimmed.startswith("postgres://")):
        raise ValueError("DATABASE_URL must start with 'postgresql://' or 'postgres://'")
    try:
        parsed = urlparse(trimmed)
        if not parsed.hostname:
            raise ValueError("DATABASE_URL must contain a valid host")
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError("Invalid DATABASE_URL format") from None
    
    # Normalize postgres:// prefix to postgresql:// for standard driver compatibility
    if trimmed.startswith("postgres://"):
        trimmed = "postgresql://" + trimmed[len("postgres://"):]
    return trimmed


class Settings:
    PROJECT_NAME: str = "PragyaX"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Security
    # Dev-only fallback. In production (ENVIRONMENT=production) a real SECRET_KEY is mandatory (see validate_production()).
    SECRET_KEY: str = os.getenv("SECRET_KEY", "pragyax-hackathon-2026-secret-salt-key")
    INSECURE_DEV_SECRET: str = "pragyax-hackathon-2026-secret-salt-key"
    # Public site URL used in share/verification links (no hard-coded domain).
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:5173").rstrip("/")

    @property
    def ADMIN_EMAILS(self) -> List[str]:
        """Server-side admin allow-list (comma-separated emails). Empty by default: nobody is admin."""
        return [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]

    @property
    def is_production(self) -> bool:
        return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"

    def validate_production(self) -> None:
        """Fail fast with a clear message when required production settings are missing."""
        if not self.is_production:
            return
        problems = []
        if self.SECRET_KEY == self.INSECURE_DEV_SECRET or len(self.SECRET_KEY) < 32:
            problems.append("SECRET_KEY must be set to a random string of at least 32 characters")
        if not self.DATABASE_URL:
            problems.append("DATABASE_URL must be set to PostgreSQL")
        if any("localhost" in o or "127.0.0.1" in o for o in self.CORS_ORIGINS):
            problems.append("CORS_ORIGINS must list only your real frontend origin(s), not localhost")
        if problems:
            raise RuntimeError("Invalid production configuration: " + "; ".join(problems))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # Database Configuration
    @property
    def DATABASE_URL(self) -> Optional[str]:
        raw = os.getenv("DATABASE_URL", "").strip()
        if not raw:
            return None
        return validate_postgres_url(raw)

    @DATABASE_URL.setter
    def DATABASE_URL(self, value: Optional[str]) -> None:
        if value:
            os.environ["DATABASE_URL"] = validate_postgres_url(value)
        else:
            os.environ.pop("DATABASE_URL", None)

    @property
    def is_postgres(self) -> bool:
        return True

    @property
    def sanitized_database_url(self) -> str:
        url = self.DATABASE_URL
        return sanitize_db_url(url) if url else ""
    
    # CORS Origins
    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [
            origin.strip() for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
            ).split(",") if origin.strip()
        ]
    
    # AI Engine
    @property
    def AI_PROVIDER(self) -> str:
        return os.getenv("AI_PROVIDER", "mock")


settings = Settings()

