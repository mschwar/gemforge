import sqlite3
from pathlib import Path
from typing import List, Set, Optional

from .graph import get_downstream_nodes

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TAINT_DB = _REPO_ROOT / "memory" / "taint_registry.db"

class TaintManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(_TAINT_DB)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tainted_nodes (
                    run_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, node_id)
                )
            """)
            conn.commit()

    def taint_node(self, run_id: str, node_id: str, reason: str = "upstream_change"):
        """Marks a node and ALL its downstream dependents as tainted."""
        affected_nodes = {node_id} | get_downstream_nodes(node_id)
        
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            for nid in affected_nodes:
                conn.execute(
                    "INSERT OR REPLACE INTO tainted_nodes (run_id, node_id, reason, created_at) VALUES (?, ?, ?, ?)",
                    (run_id, nid, reason, now)
                )
            conn.commit()
        print(f"   🚩 [TAINT] Marked {len(affected_nodes)} nodes as stale (triggered by {node_id})")

    def is_tainted(self, run_id: str, node_id: str) -> bool:
        """Checks if a specific node is tainted for a run."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM tainted_nodes WHERE run_id = ? AND node_id = ?",
                (run_id, node_id)
            )
            return cursor.fetchone() is not None

    def clear_taint(self, run_id: str, node_id: str):
        """Removes the taint from a node after it has been successfully rerun."""
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute(
                "DELETE FROM tainted_nodes WHERE run_id = ? AND node_id = ?",
                (run_id, node_id)
            )
            conn.commit()

# Singleton
taint_manager = TaintManager()
