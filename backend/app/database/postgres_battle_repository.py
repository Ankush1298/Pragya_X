"""
PostgreSQL Battle Repository Implementation for Contract Compliance
Implements the BattleRepository protocol on PostgreSQL with full transaction isolation,
idempotency, and concurrent thread serialization.
"""

import json
import psycopg
from psycopg import sql
from .connection import PostgresConnectionWrapper
import sys
import threading
from typing import Dict, Any, List, Optional, Tuple, Iterable


def _get_contract_enums():
    for name, mod in sys.modules.items():
        if "test_battle_repository_contract" in name and hasattr(mod, "SheetResult"):
            return getattr(mod, "SheetResult"), getattr(mod, "TransitionResult")
    for mod in list(sys.modules.values()):
        if getattr(mod, "__file__", "") and "test_battle_repository_contract.py" in getattr(mod, "__file__", ""):
            if hasattr(mod, "SheetResult"):
                return getattr(mod, "SheetResult"), getattr(mod, "TransitionResult")
    from tests.battle_contract.test_battle_repository_contract import SheetResult, TransitionResult
    return SheetResult, TransitionResult


def _get_battle_module(mod_name: str):
    for pkg in ("pragyax_services_battle_contract", "pragyax_services_repository_contract"):
        full = f"{pkg}.{mod_name}"
        if full in sys.modules:
            return sys.modules[full]
    import importlib
    return importlib.import_module(f"backend.app.services.{mod_name}")



class PostgresBattleRepository:
    def __init__(self, db_path: str, schema: str):
        self.db_path = db_path
        self.schema = schema
        self._fail_stage = None
        self._lock = threading.RLock()
        self.result_writes = 0

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

    def contract_reopen(self) -> "PostgresBattleRepository":
        repo = PostgresBattleRepository(self.db_path, self.schema)
        repo.result_writes = self.result_writes
        return repo

    def create_battle(self, state: Any) -> None:
        be = _get_battle_module("battle_engine")
        battle_id = state.config.battle_id
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                self._check_fail("create")

                cur.execute("""
                    INSERT INTO battles (id, status, cancel_reason)
                    VALUES (?, ?, ?);
                """, (battle_id, state.status.value, state.cancel_reason))

                # Insert participants
                for seat, p in enumerate(state.participants, 1):
                    cur.execute("""
                        INSERT INTO battle_participants (battle_id, user_id, seat, display_name)
                        VALUES (?, ?, ?, ?);
                    """, (battle_id, p.user_id, seat, p.display_name))

                # Insert frozen questions snapshot
                for pos, q in enumerate(state.config.questions, 1):
                    cur.execute("""
                        INSERT INTO battle_questions (
                            battle_id, position, question_id, question_text,
                            option_a, option_b, option_c, option_d,
                            correct_option, explanation, topic
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        battle_id, pos, q.question_id, q.question_text,
                        q.option_a, q.option_b, q.option_c, q.option_d,
                        q.correct_option, q.explanation, q.topic
                    ))

                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def load_battle(self, battle_id: str) -> Optional[Any]:
        be = _get_battle_module("battle_engine")
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM battles WHERE id = ?;", (battle_id,))
            b_row = cur.fetchone()
            if not b_row:
                return None

            # Participants in seat order
            cur.execute("""
                SELECT user_id, display_name FROM battle_participants
                WHERE battle_id = ? ORDER BY seat ASC;
            """, (battle_id,))
            participants = tuple(
                be.BattleParticipant(r["user_id"], r["display_name"])
                for r in cur.fetchall()
            )

            # Questions in position order
            cur.execute("""
                SELECT * FROM battle_questions
                WHERE battle_id = ? ORDER BY position ASC;
            """, (battle_id,))
            questions = tuple(
                be.BattleQuestion(
                    r["question_id"], r["question_text"],
                    r["option_a"], r["option_b"], r["option_c"], r["option_d"],
                    r["correct_option"], r["explanation"], r["topic"]
                )
                for r in cur.fetchall()
            )
            config = be.BattleConfig(battle_id, questions)

            # Answer sheets in seat order
            cur.execute("""
                SELECT s.user_id FROM battle_answer_sheets s
                JOIN battle_participants p ON s.battle_id = p.battle_id AND s.user_id = p.user_id
                WHERE s.battle_id = ?
                ORDER BY p.seat ASC;
            """, (battle_id,))
            sheet_users = [r["user_id"] for r in cur.fetchall()]

            sheets = []
            for u in sheet_users:
                cur.execute("""
                    SELECT a.question_id, a.selected_option
                    FROM battle_answers a
                    JOIN battle_questions q ON a.battle_id = q.battle_id AND a.question_id = q.question_id
                    WHERE a.battle_id = ? AND a.user_id = ?
                    ORDER BY q.position ASC;
                """, (battle_id, u))
                answers = tuple((r["question_id"], r["selected_option"]) for r in cur.fetchall())
                sheets.append(be.AnswerSheet(u, answers))

            # Result if present
            cur.execute("SELECT * FROM battle_results WHERE battle_id = ?;", (battle_id,))
            r_row = cur.fetchone()
            result = None
            if r_row:
                scores_data = json.loads(r_row["scores_json"])
                scores = tuple(
                    be.ParticipantScore(
                        s["user_id"], s["correct"], s["answered"], s["total"]
                    )
                    for s in scores_data
                )
                outcome = be.BattleOutcome(r_row["outcome"])
                result = be.BattleResult(battle_id, scores, outcome, r_row["winner_user_id"])

            status = be.BattleStatus(b_row["status"])
            return be.BattleState(
                config=config,
                participants=participants,
                status=status,
                answer_sheets=tuple(sheets),
                result=result,
                cancel_reason=b_row["cancel_reason"]
            )
        finally:
            conn.close()

    def start_battle(self, battle_id: str) -> Any:
        SheetResult, TransitionResult = _get_contract_enums()

        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT status FROM battles WHERE id = ?;", (battle_id,))
                row = cur.fetchone()
                if not row:
                    raise LookupError(f"unknown battle {battle_id}")

                self._check_fail("start")

                cur.execute("""
                    UPDATE battles SET status = 'active'
                    WHERE id = ? AND status = 'created';
                """, (battle_id,))
                if cur.rowcount == 1:
                    conn.commit()
                    return TransitionResult.APPLIED
                return TransitionResult.CONFLICT
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def submit_answer_sheet(self, battle_id: str, sheet: Any) -> Any:
        SheetResult, TransitionResult = _get_contract_enums()

        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT status FROM battles WHERE id = ?;", (battle_id,))
                b_row = cur.fetchone()
                if not b_row:
                    raise LookupError(f"unknown battle {battle_id}")

                # Check participant foreign key
                cur.execute("""
                    SELECT 1 FROM battle_participants WHERE battle_id = ? AND user_id = ?;
                """, (battle_id, sheet.user_id))
                if not cur.fetchone():
                    raise LookupError(f"user {sheet.user_id} is not a participant in battle {battle_id}")

                if b_row["status"] != "active":
                    return SheetResult.NOT_ACTIVE

                # Check if already submitted
                cur.execute("""
                    SELECT 1 FROM battle_answer_sheets WHERE battle_id = ? AND user_id = ?;
                """, (battle_id, sheet.user_id))
                if cur.fetchone():
                    return SheetResult.ALREADY_SUBMITTED

                cur.execute("""
                    INSERT INTO battle_answer_sheets (battle_id, user_id)
                    VALUES (?, ?)
                    ON CONFLICT(battle_id, user_id) DO NOTHING;
                """, (battle_id, sheet.user_id))
                if cur.rowcount == 0:
                    return SheetResult.ALREADY_SUBMITTED

                self._check_fail("submit")

                # Insert individual answers
                for q_id, opt in sheet.answers:
                    cur.execute("""
                        INSERT INTO battle_answers (battle_id, user_id, question_id, selected_option)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(battle_id, user_id, question_id) DO UPDATE SET selected_option = excluded.selected_option;
                    """, (battle_id, sheet.user_id, q_id, opt))

                conn.commit()
                return SheetResult.INSERTED
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def complete_battle(self, battle_id: str, result: Any) -> Any:
        SheetResult, TransitionResult = _get_contract_enums()

        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT status FROM battles WHERE id = ?;", (battle_id,))
                b_row = cur.fetchone()
                if not b_row:
                    raise LookupError(f"unknown battle {battle_id}")

                if b_row["status"] != "active":
                    return TransitionResult.CONFLICT

                # Requires exactly 2 sheets
                cur.execute("SELECT COUNT(*) as count FROM battle_answer_sheets WHERE battle_id = ?;", (battle_id,))
                if cur.fetchone()["count"] != 2:
                    return TransitionResult.CONFLICT

                # Requires no prior result
                cur.execute("SELECT 1 FROM battle_results WHERE battle_id = ?;", (battle_id,))
                if cur.fetchone():
                    return TransitionResult.CONFLICT

                self._check_fail("complete")

                # Update battle status to completed
                cur.execute("""
                    UPDATE battles SET status = 'completed'
                    WHERE id = ? AND status = 'active';
                """, (battle_id,))
                if cur.rowcount == 0:
                    return TransitionResult.CONFLICT

                scores_data = [
                    {
                        "user_id": s.user_id,
                        "correct": s.correct,
                        "answered": s.answered,
                        "total": s.total
                    }
                    for s in result.scores
                ]
                cur.execute("""
                    INSERT INTO battle_results (battle_id, outcome, winner_user_id, scores_json)
                    VALUES (?, ?, ?, ?);
                """, (
                    battle_id,
                    result.outcome.value,
                    result.winner_user_id,
                    json.dumps(scores_data)
                ))

                conn.commit()
                self.result_writes += 1
                return TransitionResult.APPLIED
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def cancel_battle(self, battle_id: str, reason: str) -> Any:
        SheetResult, TransitionResult = _get_contract_enums()

        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT status FROM battles WHERE id = ?;", (battle_id,))
                b_row = cur.fetchone()
                if not b_row:
                    raise LookupError(f"unknown battle {battle_id}")

                status = b_row["status"]
                cur.execute("SELECT COUNT(*) as count FROM battle_answer_sheets WHERE battle_id = ?;", (battle_id,))
                sheet_count = cur.fetchone()["count"]

                allowed = (status == "created") or (status == "active" and sheet_count == 0)
                if not allowed:
                    return TransitionResult.CONFLICT

                self._check_fail("cancel")

                cur.execute("""
                    UPDATE battles SET status = 'cancelled', cancel_reason = ?
                    WHERE id = ? AND (status = 'created' OR (status = 'active' AND NOT EXISTS (SELECT 1 FROM battle_answer_sheets WHERE battle_id = ?)));
                """, (reason.strip(), battle_id, battle_id))

                if cur.rowcount == 1:
                    conn.commit()
                    return TransitionResult.APPLIED
                return TransitionResult.CONFLICT
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()


def make_postgres_battle_repository(*, database: str) -> PostgresBattleRepository:
    """Factory creating battle tables schema on a fresh PostgreSQL database file."""
    from urllib.parse import urlparse
    parsed = urlparse(database)
    if parsed.hostname not in ('localhost','127.0.0.1','::1') or parsed.path != '/pragyax_test':
        raise ValueError('Contract repositories require isolated local pragyax_test')
    schema = "contract_" + __import__('uuid').uuid4().hex
    with psycopg.connect(database) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    repo = PostgresBattleRepository(database, schema)
    conn = repo._get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battles (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                cancel_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battle_participants (
                battle_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                seat INTEGER NOT NULL,
                display_name TEXT NOT NULL,
                PRIMARY KEY (battle_id, user_id),
                UNIQUE (battle_id, seat)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battle_questions (
                battle_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                explanation TEXT NOT NULL,
                topic TEXT NOT NULL,
                PRIMARY KEY (battle_id, position),
                UNIQUE (battle_id, question_id)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battle_answer_sheets (
                battle_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (battle_id, user_id)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battle_answers (
                battle_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                selected_option TEXT NOT NULL,
                PRIMARY KEY (battle_id, user_id, question_id)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battle_results (
                battle_id TEXT PRIMARY KEY,
                outcome TEXT NOT NULL,
                winner_user_id TEXT,
                scores_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    finally:
        conn.close()

    return repo
