import re
import json
from pathlib import Path
from core.memory.lessons_manager import LessonsManager
from core.memory.user_taste_manager import UserTasteManager

def parse_and_log_weaver_output(llm_output: str, gem_id: str):
    """Parses Weaver output blocks and updates DB/Taste."""
    lessons_mgr = LessonsManager()
    taste_mgr = UserTasteManager()
    
    # 1. Lessons
    lesson_pattern = r"===LESSON===\n(.*?)(?=\n===|\Z)"
    lesson_blocks = re.findall(lesson_pattern, llm_output, re.DOTALL)
    for block in lesson_blocks:
        data = {}
        for line in block.strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip().lower().replace(" ", "_")] = v.strip()
        
        impact_val = 5
        try:
            impact_val = int(data.get("impact", 5))
        except:
            pass

        lessons_mgr.log_lesson(
            gem_id=gem_id,
            category=data.get("category", "general"),
            lesson=data.get("lesson", "N/A"),
            impact=impact_val,
            related_agents=data.get("related_agents", "").split(",")
        )

    # 2. Taste Updates
    taste_pattern = r"===TASTE_UPDATE===\n(.*?)(?=\n===|\Z)"
    taste_blocks = re.findall(taste_pattern, llm_output, re.DOTALL)
    for block in taste_blocks:
        data = {}
        for line in block.strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip().lower()] = v.strip()
        
        if "feedback" in data:
            weight_val = 10
            try:
                weight_val = int(data.get("weight", 10))
            except:
                pass
            
            taste_mgr.add_feedback(
                feedback=data["feedback"],
                category=data.get("category", "general"),
                weight=weight_val
            )
    
    return {"lessons_count": len(lesson_blocks), "taste_updates_count": len(taste_blocks)}
