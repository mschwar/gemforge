import json
from pathlib import Path
from datetime import datetime

class UserTasteManager:
    def __init__(self, path: str = "memory/user_taste.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._init_default()
        self.data = json.loads(self.path.read_text())

    def _init_default(self):
        default = {
            "core_values": ["clean minimal code", "maximum user delight", "fast iteration", "no bloat", "rock-solid foundations"],
            "ui_ux_style": "Apple-style aesthetics (high whitespace, bold typography, smooth transitions) applied to ANY platform.",
            "tech_preferences": {
                "mobile": "Strictly follow request (SwiftUI, Flutter, or RN)",
                "web": "React + TypeScript + Tailwind",
                "backend": "lightweight",
                "cli": "Python + Rich"
            },
            "avoid": ["over-engineering", "ignoring explicit platform requests", "complex state without reason", "poor git hygiene"],
            "feedback_history": [],
            "last_updated": datetime.now().isoformat()
        }
        self.path.write_text(json.dumps(default, indent=2))

    def add_feedback(self, feedback: str, category: str = "general", weight: int = 10):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback,
            "category": category,
            "weight": weight
        }
        self.data["feedback_history"].append(entry)
        self.data["last_updated"] = datetime.now().isoformat()
        self.path.write_text(json.dumps(self.data, indent=2))

    def get_context_for_evolver(self, max_entries: int = 15) -> str:
        """Returns formatted string to inject into every evolution prompt."""
        lines = ["=== USER TASTE MEMORY (HIGH PRIORITY) ==="]
        for k, v in self.data.items():
            if k not in ["feedback_history"]:
                lines.append(f"{k.upper()}: {v}")
        lines.append("\nRecent feedback (highest weight first):")
        for entry in sorted(self.data["feedback_history"], key=lambda x: x["weight"], reverse=True)[:max_entries]:
            lines.append(f"[{entry['category']}] {entry['feedback']}")
        return "\n".join(lines)
