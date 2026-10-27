"""
PostgreSQL Gamification Repository Implementation for Contract Compliance
Implements the GamificationRepository protocol on PostgreSQL with full transaction isolation,
idempotency, and concurrent thread serialization.
"""

import json
import psycopg
from psycopg import sql
from .connection import PostgresConnectionWrapper
import sys
import threading
import uuid
from typing import Dict, Any, List, Optional, Tuple, Iterable, Set


def _get_services_module(mod_name: str):
    for pkg in ("pragyax_services_repository_contract", "pragyax_services_battle_contract"):
        full = f"{pkg}.{mod_name}"
        if full in sys.modules:
            return sys.modules[full]
    import importlib
    return importlib.import_module(f"backend.app.services.{mod_name}")


class PostgresGamificationRepository:
    def __init__(self, db_path: str, schema: str):
        self.db_path = db_path
        self.schema = schema
        self._fail_stage = None
        self._lock = threading.RLock()

    def _get_connection(self):
        from psycopg.rows import dict_row
        conn = psycopg.connect(self.db_path, row_factory=dict_row)
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
        # A transaction-level PostgreSQL lock protects independent repository instances.
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (self.schema,))
        return PostgresConnectionWrapper(conn)

    def contract_fail_next_write(self, stage: str) -> None:
        self._fail_stage = stage

    def _check_fail(self, stage: str) -> None:
        if self._fail_stage == stage:
            self._fail_stage = None
            raise RuntimeError(f"injected failure at {stage}")

    def get_challenge(self, challenge_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM daily_challenges WHERE id = ?;", (challenge_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            # Ensure JSON serializable
            json.dumps(res)
            return res
        finally:
            conn.close()

    def has_completed_challenge(self, user_id: str, challenge_id: str) -> bool:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM user_challenge_submissions WHERE user_id = ? AND challenge_id = ?;",
                (user_id, challenge_id)
            )
            return cur.fetchone() is not None
        finally:
            conn.close()

    def get_badge_keys(self, user_id: str) -> frozenset:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT badge_key FROM user_badges WHERE user_id = ?;", (user_id,))
            rows = cur.fetchall()
            return frozenset(r["badge_key"] for r in rows)
        finally:
            conn.close()

    def record_challenge_outcome(self, write: Any) -> Any:
        # Validate write object
        if not hasattr(write, "user_id") or not hasattr(write, "challenge_id") or not hasattr(write, "selected_option"):
            raise TypeError("write must be a ChallengeWrite instance")
        if type(write).__name__ != "ChallengeWrite":
            raise TypeError("write must be a ChallengeWrite instance")

        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()

                # Foreign key checks (unknown user / challenge raises LookupError)
                cur.execute("SELECT 1 FROM users WHERE id = ?;", (write.user_id,))
                if not cur.fetchone():
                    raise LookupError(f"unknown user {write.user_id}")
                cur.execute("SELECT 1 FROM daily_challenges WHERE id = ?;", (write.challenge_id,))
                if not cur.fetchone():
                    raise LookupError(f"unknown challenge {write.challenge_id}")

                gi_mod = sys.modules.get(write.__class__.__module__) or _get_services_module("gamification_integration")
                # Check if already completed
                cur.execute(
                    "SELECT 1 FROM user_challenge_submissions WHERE user_id = ? AND challenge_id = ?;",
                    (write.user_id, write.challenge_id)
                )
                if cur.fetchone():
                    return gi_mod.WriteResult.ALREADY_COMPLETED

                # Insert submission
                sub_id = f"csub_{uuid.uuid4().hex[:12]}"
                cur.execute("""
                    INSERT INTO user_challenge_submissions (
                        id, user_id, challenge_id, selected_option, is_correct, points_awarded
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, challenge_id) DO NOTHING;
                """, (
                    sub_id,
                    write.user_id,
                    write.challenge_id,
                    write.selected_option,
                    1 if write.is_correct else 0,
                    write.points_awarded
                ))

                if cur.rowcount == 0:
                    return gi_mod.WriteResult.ALREADY_COMPLETED

                self._check_fail("ledger")

                # Insert ledger event
                if write.ledger_event is not None:
                    cur.execute("""
                        INSERT INTO points_ledger (
                            id, event_key, user_id, points_delta, origin, source_type
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(event_key) DO NOTHING;
                    """, (
                        write.ledger_event.event_id,
                        write.ledger_event.event_key,
                        write.ledger_event.user_id,
                        write.ledger_event.points_delta,
                        str(write.ledger_event.origin),
                        write.ledger_event.source_type
                    ))

                self._check_fail("badges")

                # Insert badges
                for award in write.badges:
                    badge_id = f"badge_{uuid.uuid4().hex[:12]}"
                    cur.execute("""
                        INSERT INTO user_badges (
                            id, user_id, badge_key, title, description, icon
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(user_id, badge_key) DO NOTHING;
                    """, (
                        badge_id,
                        write.user_id,
                        award.badge_key,
                        getattr(award, "title", award.badge_key),
                        getattr(award, "description", ""),
                        getattr(award, "icon", "award")
                    ))

                conn.commit()
                gi_mod = sys.modules.get(write.__class__.__module__) or _get_services_module("gamification_integration")
                return gi_mod.WriteResult.INSERTED
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def insert_badges(self, user_id: str, awards: Tuple[Any, ...]) -> Tuple[str, ...]:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM users WHERE id = ?;", (user_id,))
                if not cur.fetchone():
                    raise LookupError(f"unknown user {user_id}")

                for award in awards:
                    if not hasattr(award, "badge_key"):
                        raise TypeError("awards must be AchievementAward items")
                    if type(award).__name__ != "AchievementAward":
                        raise TypeError("awards must be AchievementAward items")

                cur.execute("SELECT badge_key FROM user_badges WHERE user_id = ?;", (user_id,))
                held = set(r["badge_key"] for r in cur.fetchall())

                inserted = []
                for award in awards:
                    if award.badge_key not in held:
                        badge_id = f"badge_{uuid.uuid4().hex[:12]}"
                        cur.execute("""
                            INSERT INTO user_badges (
                                id, user_id, badge_key, title, description, icon
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(user_id, badge_key) DO NOTHING;
                        """, (
                            badge_id,
                            user_id,
                            award.badge_key,
                            getattr(award, "title", award.badge_key),
                            getattr(award, "description", ""),
                            getattr(award, "icon", "award")
                        ))
                        if cur.rowcount > 0:
                            inserted.append(award.badge_key)
                            held.add(award.badge_key)

                self._check_fail("badges")
                conn.commit()
                return tuple(inserted)
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def get_reward_records(self, user_id: str) -> List[Any]:
        gs_mod = _get_services_module("gamification_service")
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT event_key, points_delta FROM points_ledger WHERE user_id = ?;", (user_id,))
            rows = cur.fetchall()
            return [gs_mod.RewardRecord(r["event_key"], r["points_delta"]) for r in rows]
        finally:
            conn.close()


def make_postgres_gamification_repository(seed, *, database: str) -> PostgresGamificationRepository:
    """Factory creating schema and seeding data per ContractSeed into database path."""
    from urllib.parse import urlparse
    parsed = urlparse(database)
    if parsed.hostname not in ('localhost','127.0.0.1','::1') or parsed.path != '/pragyax_test':
        raise ValueError('Contract repositories require isolated local pragyax_test')
    schema = "contract_" + __import__('uuid').uuid4().hex
    with psycopg.connect(database) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    repo = PostgresGamificationRepository(database, schema)
    conn = repo._get_connection()
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY);")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_challenges (
                id TEXT PRIMARY KEY,
                title TEXT,
                topic TEXT,
                difficulty TEXT,
                description TEXT,
                code_snippet TEXT,
                question_type TEXT,
                option_a TEXT,
                option_b TEXT,
                option_c TEXT,
                option_d TEXT,
                correct_option TEXT,
                explanation TEXT,
                points INTEGER
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_challenge_submissions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                challenge_id TEXT NOT NULL,
                selected_option TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                points_awarded INTEGER NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, challenge_id)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS points_ledger (
                id TEXT PRIMARY KEY,
                event_key TEXT UNIQUE,
                user_id TEXT NOT NULL,
                points_delta INTEGER NOT NULL,
                origin TEXT,
                source_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_badges (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                badge_key TEXT NOT NULL,
                title TEXT,
                description TEXT,
                icon TEXT,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, badge_key)
            );
        """)

        # Seed users
        for u in seed.users:
            cur.execute("INSERT INTO users (id) VALUES (?) ON CONFLICT DO NOTHING;", (u,))

        # Seed challenges
        for ch in seed.challenges:
            cur.execute("""
                INSERT INTO daily_challenges (
                    id, title, topic, difficulty, description, code_snippet,
                    question_type, option_a, option_b, option_c, option_d,
                    correct_option, explanation, points
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                ch["id"], ch["title"], ch["topic"], ch["difficulty"],
                ch["description"], ch["code_snippet"], ch["question_type"],
                ch["option_a"], ch["option_b"], ch["option_c"], ch["option_d"],
                ch["correct_option"], ch["explanation"], ch["points"]
            ))

        # Seed badges
        for u, badge_keys in seed.badges.items():
            for b in badge_keys:
                cur.execute("""
                    INSERT INTO user_badges (id, user_id, badge_key, title, description, icon)
                    VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING;
                """, (f"b_{uuid.uuid4().hex[:10]}", u, b, b, "", "award"))

        conn.commit()
    finally:
        conn.close()

    return repo
