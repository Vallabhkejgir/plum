from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.models import ClaimRecord, EvalRunResult


class ClaimsRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._ensure_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS eval_runs (
                    run_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save_claim(self, record: ClaimRecord) -> None:
        payload = record.model_dump(mode="json")
        now = datetime.utcnow().isoformat()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO claims (claim_id, status, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(claim_id) DO UPDATE SET
                    status=excluded.status,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (record.claim_id, record.status.value, json.dumps(payload), now),
            )
            connection.commit()

    def get_claim(self, claim_id: str) -> ClaimRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM claims WHERE claim_id = ?",
                (claim_id,),
            ).fetchone()
        if not row:
            return None
        return ClaimRecord.model_validate(json.loads(row["payload_json"]))

    def save_eval_run(self, result: EvalRunResult) -> None:
        payload = result.model_dump(mode="json")
        now = datetime.utcnow().isoformat()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO eval_runs (run_id, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (result.run_id, json.dumps(payload), now),
            )
            connection.commit()

    def get_eval_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM eval_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])
