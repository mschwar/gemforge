import os
from pathlib import Path

from core.memory.lessons_manager import LessonsManager
from core.memory.user_taste_manager import UserTasteManager


class EmpireStats:
    def __init__(self, projects_root: str = None):
        if not projects_root:
            from tools.file_tools import PROJECTS_ROOT
            self.projects_root = PROJECTS_ROOT
        else:
            self.projects_root = Path(projects_root)
        self.lessons_mgr = LessonsManager()
        self.taste_mgr = UserTasteManager()
        self.checkpoints_db = "checkpoints.db"

    def get_total_costs(self) -> float:
        """Sum of all recorded pipeline session costs from checkpoints.db."""
        from tools.cost_tracker import cost_tracker
        return cost_tracker.get_cumulative_cost()

    def get_project_count(self):
        if not self.projects_root.exists():
            return 0
        return len([d for d in self.projects_root.iterdir() if d.is_dir()])

    def get_recent_projects(self, limit: int = 10):
        if not self.projects_root.exists():
            return []
        
        projects = []
        for d in sorted(self.projects_root.iterdir(), key=os.path.getmtime, reverse=True):
            if d.is_dir():
                projects.append({
                    "name": d.name,
                    "path": str(d),
                    "created": os.path.getmtime(d),
                    "has_xcode": any(f.endswith(".xcodeproj") for f in os.listdir(d))
                })
            if len(projects) >= limit:
                break
        return projects

    def get_weaver_stats(self):
        lessons = self.lessons_mgr.get_recent_lessons(limit=5)
        taste = self.taste_mgr.data
        return {
            "total_lessons": len(self.lessons_mgr.get_recent_lessons(limit=1000)),
            "recent_lessons": lessons,
            "core_values": taste.get("core_values", []),
            "tech_prefs": taste.get("tech_preferences", {})
        }

empire_stats = EmpireStats()
