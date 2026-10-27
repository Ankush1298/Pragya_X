"""Explicit PostgreSQL schema migration command. Never run automatically at startup."""
from pathlib import Path
import hashlib
import re
import psycopg
from ..config import settings

MIGRATIONS = Path(__file__).resolve().parents[3] / 'database' / 'migrations'


def migration_files():
    return sorted(MIGRATIONS.glob('[0-9][0-9][0-9][0-9]_*.sql'))


def pending_migrations(url):
    with psycopg.connect(url) as conn:
        if not conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0]:
            return [p.name for p in migration_files()]
        applied = {r[0] for r in conn.execute('SELECT version FROM schema_migrations')}
        return [p.name for p in migration_files() if p.name not in applied]


def migrate(url):
    """Apply ordered, checksummed migrations under one session advisory lock."""
    if not url:
        raise RuntimeError('DATABASE_URL is required for PostgreSQL migrations')
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute('SELECT pg_advisory_lock(724130611)')
        try:
            conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations '
                         '(version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TIMESTAMPTZ DEFAULT now())')
            for path in migration_files():
                content = path.read_text()
                digest = hashlib.sha256(content.encode()).hexdigest()
                existing = conn.execute('SELECT checksum FROM schema_migrations WHERE version=%s', (path.name,)).fetchone()
                if existing:
                    if existing[0] != digest:
                        raise RuntimeError(f'Applied migration changed: {path.name}; create a forward migration')
                    continue
                # Existing SQL files contain transaction markers; the runner owns the transaction.
                content = re.sub(r'^\s*(BEGIN|COMMIT);\s*$', '', content, flags=re.M)
                with conn.transaction():
                    conn.execute(content)
                    conn.execute('INSERT INTO schema_migrations(version,checksum) VALUES (%s,%s)', (path.name,digest))
        finally:
            conn.execute('SELECT pg_advisory_unlock(724130611)')


if __name__ == '__main__':
    migrate(settings.DATABASE_URL)
    print('PostgreSQL migrations applied successfully.')
