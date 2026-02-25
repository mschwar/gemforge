import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class OutboxStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).resolve().parent.parent.parent / "checkpoints.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 5,
                    published INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_outbox_prio ON event_outbox(published, priority, id)")
            conn.commit()

    def save_event(self, event_dict: Dict[str, Any]):
        priority = event_dict.get("priority", 5)
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute(
                "INSERT INTO event_outbox (event_json, priority, published, created_at) VALUES (?, ?, 0, ?)",
                (json.dumps(event_dict), priority, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

    def get_unpublished_events(self, limit: int = 100, event_type_prefix: Optional[str] = None, exclude_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM event_outbox WHERE published = 0"
            params = []
            
            if event_type_prefix:
                query += " AND json_extract(event_json, '$.event_type') LIKE ?"
                params.append(f"{event_type_prefix}%")
                
            if exclude_prefix:
                query += " AND json_extract(event_json, '$.event_type') NOT LIKE ?"
                params.append(f"{exclude_prefix}%")
                
            query += " ORDER BY priority ASC, id ASC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def mark_as_published(self, event_ids: List[int]):
        if not event_ids:
            return
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            placeholders = ",".join("?" for _ in event_ids)
            conn.execute(
                f"UPDATE event_outbox SET published = 1 WHERE id IN ({placeholders})",
                event_ids
            )
            conn.commit()

# Global singleton
outbox_store = OutboxStore()
