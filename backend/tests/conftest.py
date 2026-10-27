"""All persistence tests use a guarded, dedicated local PostgreSQL database."""
import os
from urllib.parse import urlparse
import pytest


def pytest_configure(config):
    url = os.getenv('TEST_DATABASE_URL','')
    parsed = urlparse(url)
    if parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.path != '/pragyax_test':
        raise pytest.UsageError('Set TEST_DATABASE_URL to a dedicated local PostgreSQL database named pragyax_test.')
    os.environ['DATABASE_URL'] = url
    os.environ['AI_PROVIDER'] = 'mock'
    os.environ['PRAGYAX_CONTRACT_POSTGRES_FACTORY'] = 'backend.app.database.postgres_gamification_repository:make_postgres_gamification_repository'
    os.environ['PRAGYAX_BATTLE_CONTRACT_POSTGRES_FACTORY'] = 'backend.app.database.postgres_battle_repository:make_postgres_battle_repository'
    from backend.app.database.migrate import migrate
    migrate(url)


def clear_activity():
    from backend.app.database.connection import close_db_pool, get_db
    close_db_pool()
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        preserve={'schema_migrations','subjects','assessment_questions','daily_challenges','challenge_library','reward_catalog','organizations'}
        names=[r['tablename'] for r in cur.fetchall() if r['tablename'] not in preserve]
        from psycopg import sql
        cur.execute(sql.SQL('TRUNCATE {} CASCADE').format(sql.SQL(',').join(map(sql.Identifier,names))))


@pytest.fixture(scope='module',autouse=True)
def module_database():
    clear_activity()
    yield


@pytest.fixture
def reset_postgres_data():
    clear_activity()
    yield


@pytest.fixture(autouse=True)
def restore_database_configuration():
    yield
    from backend.app.database.connection import close_db_pool
    os.environ['DATABASE_URL']=os.environ['TEST_DATABASE_URL']
    close_db_pool()
