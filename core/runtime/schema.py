from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

@dataclass
class StepEvent:
    run_id: str
    step_id: str
    event_type: str  # e.g., "step.started", "step.completed", "step.failed"
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1 (high) to 10 (low)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attempt: int = 0
