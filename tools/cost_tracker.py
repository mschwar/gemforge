"""
GemForge — Cost & Rate-Limit Awareness (Module 5)
Tracks Anthropic tokens + estimated $ cost per call.
Persists cumulative totals in checkpoints.db so the Empire Dashboard
shows real numbers across sessions.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "checkpoints.db"


class CostTracker:
    def __init__(self):
        # In-session counters (reset each process)
        self.total_tokens = 0
        self.total_cost = 0.0
        self.calls = 0
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_history (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT    NOT NULL,
                    tokens    INTEGER NOT NULL,
                    cost_usd  REAL    NOT NULL,
                    calls     INTEGER NOT NULL
                )
            """)
            self._conn.commit()
        return self._conn

    def _persist_session(self):
        """Write the current session totals to the DB."""
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO cost_history (timestamp, tokens, cost_usd, calls) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), self.total_tokens, self.total_cost, self.calls),
            )
            conn.commit()
        except Exception:
            pass  # Never let persistence errors break the pipeline

    def get_cumulative_cost(self) -> float:
        """Sum of all recorded sessions (excludes the current in-progress session)."""
        try:
            conn = self._get_conn()
            row = conn.execute("SELECT COALESCE(SUM(cost_usd), 0.0) FROM cost_history").fetchone()
            return float(row[0]) if row else 0.0
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Core tracking
    # ------------------------------------------------------------------

    def track_call(self, response) -> dict:
        """Extract usage from Anthropic response and update totals."""
        if hasattr(response, "usage"):
            input_t = response.usage.input_tokens
            output_t = response.usage.output_tokens
            # Claude 3 Haiku pricing: $0.25/M input, $1.25/M output
            cost = (input_t * 0.00000025 + output_t * 0.00000125)
        else:
            input_t = output_t = cost = 0

        self.total_tokens += input_t + output_t
        self.total_cost += cost
        self.calls += 1

        return {
            "tokens": input_t + output_t,
            "cost": round(cost, 6),
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "calls": self.calls,
        }

    def finalize_session(self):
        """Call at the end of a pipeline run to persist this session's cost."""
        if self.calls > 0:
            self._persist_session()


cost_tracker = CostTracker()
