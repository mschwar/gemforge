import sqlite3
import json
from datetime import datetime
from pathlib import Path

class LessonsManager:
    def __init__(self, db_path: str = "lessons/lessons.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gem_id TEXT,
                timestamp TEXT,
                category TEXT,
                lesson TEXT,
                impact INTEGER,          -- 1-10
                related_agents TEXT,     -- JSON array
                source TEXT,
                metadata TEXT
            )
        """)
        self.conn.commit()

    def log_lesson(self, gem_id: str, category: str, lesson: str, impact: int = 5,
                   related_agents: list = None, source: str = "reflector", metadata: dict = None):
        ts = datetime.now().isoformat()
        related = json.dumps(related_agents or [])
        meta = json.dumps(metadata or {})
        self.conn.execute(
            "INSERT INTO lessons (gem_id, timestamp, category, lesson, impact, related_agents, source, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (gem_id, ts, category, lesson, impact, related, source, meta)
        )
        self.conn.commit()
        self._append_to_lessons_md(gem_id, ts, category, lesson, impact)

    def _append_to_lessons_md(self, gem_id, ts, category, lesson, impact):
        md_path = Path("LESSONS.md")
        if not md_path.exists():
            md_path.write_text("# GemForge LESSONS.md

")
        with open(md_path, "a") as f:
            f.write(f"
## {ts} – {gem_id} [{category.upper()}] Impact:{impact}/10
")
            f.write(f"{lesson}

")

    def get_recent_lessons(self, limit: int = 50, min_impact: int = 0):
        cur = self.conn.execute(
            "SELECT * FROM lessons WHERE impact >= ? ORDER BY timestamp DESC LIMIT ?",
            (min_impact, limit)
        )
        return cur.fetchall()

    def get_for_evolver(self, limit: int = 20):
        # Returns lessons ready for prompt evolution
        return self.get_recent_lessons(limit=limit, min_impact=6)
