"""
RecoveryOS V3 — Durable Persistence & Idempotency Store (SQLite Backend)

Provides durable process-restart resilient storage for:
- Payment failure events (idempotency deduplication)
- Failure decision state
- Execution tracking records
- Cryptographically-identified audit lineage log
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "recoveryos_v3_state.db"


class DurableStateStore:
    """SQLite-backed persistent store surviving application restarts."""
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _init_sqlite(self):
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    failure_id TEXT,
                    payment_id TEXT,
                    customer_id TEXT,
                    payload_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    event_id TEXT,
                    failure_id TEXT,
                    customer_id TEXT,
                    candidate_action TEXT,
                    estimated_probability REAL,
                    expected_net REAL,
                    policy_result TEXT,
                    record_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    decision_id TEXT,
                    failure_id TEXT,
                    execution_status TEXT,
                    execution_result TEXT,
                    record_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_events_failure_id
                ON events(failure_id) WHERE failure_id IS NOT NULL AND failure_id != ''
            """)
            conn.commit()

    def is_duplicate_event(self, event_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM events WHERE event_id = ?", (event_id,))
            return cursor.fetchone() is not None

    def is_duplicate_failure(self, failure_id: str) -> bool:
        if not failure_id:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM events WHERE failure_id = ?", (failure_id,))
            return cursor.fetchone() is not None

    def get_event_record(self, event_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT record_json FROM decisions WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            if row and row["record_json"]:
                return json.loads(row["record_json"])
            cursor.execute("SELECT payload_json FROM events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            if row and row["payload_json"]:
                return json.loads(row["payload_json"])
            return None

    def get_failure_record(self, failure_id: str) -> Optional[Dict[str, Any]]:
        if not failure_id:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT record_json FROM decisions WHERE failure_id = ?", (failure_id,))
            row = cursor.fetchone()
            if row and row["record_json"]:
                return json.loads(row["record_json"])
            cursor.execute("SELECT payload_json FROM events WHERE failure_id = ?", (failure_id,))
            row = cursor.fetchone()
            if row and row["payload_json"]:
                return json.loads(row["payload_json"])
            return None

    def claim_event_and_failure(self, event_id: str, failure_id: str, payment_id: str, customer_id: str, payload_dict: Dict[str, Any]) -> bool:
        """
        Atomically claims event_id and failure_id in SQLite database before action execution.
        Returns True if claim succeeded, False if already claimed/inserted by another request.
        """
        rec_json = json.dumps(payload_dict)
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if event_id:
                    cursor.execute("SELECT 1 FROM events WHERE event_id = ?", (event_id,))
                    if cursor.fetchone() is not None:
                        return False
                if failure_id:
                    cursor.execute("SELECT 1 FROM events WHERE failure_id = ?", (failure_id,))
                    if cursor.fetchone() is not None:
                        return False
                cursor.execute(
                    "INSERT INTO events (event_id, failure_id, payment_id, customer_id, payload_json) VALUES (?, ?, ?, ?, ?)",
                    (event_id, failure_id, payment_id, customer_id, rec_json)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
        except Exception:
            return False

    def record_event_and_decision(self, event_id: str, failure_id: str, payment_id: str, customer_id: str, decision_record: Dict[str, Any]):
        rec_json = json.dumps(decision_record)
        dec_id = decision_record.get("decision_id", f"DEC_{event_id}")
        action = decision_record.get("candidate_action", "STOP")
        prob = float(decision_record.get("estimated_recovery_probability", 0.0))
        net = float(decision_record.get("expected_net_recovery", 0.0))
        pol = decision_record.get("policy_result", "STOP")

        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO events (event_id, failure_id, payment_id, customer_id, payload_json) VALUES (?, ?, ?, ?, ?)",
                (event_id, failure_id, payment_id, customer_id, rec_json)
            )
            conn.execute(
                "INSERT OR REPLACE INTO decisions (decision_id, event_id, failure_id, customer_id, candidate_action, estimated_probability, expected_net, policy_result, record_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (dec_id, event_id, failure_id, customer_id, action, prob, net, pol, rec_json)
            )
            conn.commit()

    def record_execution(self, execution_id: str, decision_id: str, failure_id: str, execution_status: str, execution_result: str, record_dict: Dict[str, Any]):
        rec_json = json.dumps(record_dict)
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO executions (execution_id, decision_id, failure_id, execution_status, execution_result, record_json) VALUES (?, ?, ?, ?, ?, ?)",
                (execution_id, decision_id, failure_id, execution_status, execution_result, rec_json)
            )
            conn.commit()

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT record_json FROM decisions ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [json.loads(r["record_json"]) for r in rows if r["record_json"]]
