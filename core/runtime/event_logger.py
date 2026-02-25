import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .schema import StepEvent

class EventLogger:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to repo root checkpoints.db
            db_path = str(Path(__file__).resolve().parent.parent.parent / "checkpoints.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS step_events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON step_events(run_id)")
            conn.commit()

    def log_event(self, event: StepEvent):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO step_events (event_id, run_id, step_id, event_type, attempt, payload_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    event.run_id,
                    event.step_id,
                    event.event_type,
                    event.attempt,
                    json.dumps(event.payload),
                    event.created_at
                )
            )
            conn.commit()

    def get_run_events(self, run_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM step_events WHERE run_id = ? ORDER BY created_at ASC",
                (run_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_runs(self, limit: int = 10) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT DISTINCT run_id FROM step_events ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [row[0] for row in cursor.fetchall()]

# Global singleton instance for easier node usage
event_logger = EventLogger()
