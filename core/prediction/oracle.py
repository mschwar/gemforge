import json
import re
from pathlib import Path
from core.memory.lessons_manager import LessonsManager
from core.memory.user_taste_manager import UserTasteManager
from pipeline import cost_aware_invoke, load_prompt
from langchain_core.messages import SystemMessage, HumanMessage

class Oracle:
    def __init__(self):
        self.lessons_mgr = LessonsManager()
        self.taste_mgr = UserTasteManager()

    def generate_predictions(self) -> list:
        """
        Uses the Oracle (Agent 27) to generate high-ROI ideas.
        Returns a list of idea dictionaries.
        """
        print(f"🔮 The Oracle is meditating on your taste and market trends...")
        
        prompt = load_prompt("27_predictive_idea_engine.md")
        
        # Gather deep context (Pillar 1+8)
        taste_context = self.taste_mgr.get_context_for_evolver()
        recent_lessons = self.lessons_mgr.get_recent_lessons(limit=10)
        lessons_summary = "\n".join([f"- {l[4]} ({l[3]})" for l in recent_lessons])
        
        user_content = f"""
USER_TASTE:
{taste_context}

LESSONS_FROM_PAST_GEMS:
{lessons_summary}

Predict 3 high-ROI ideas now.
"""
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=user_content)
        ]
        
        response = cost_aware_invoke(messages)
        
        # Parse JSON output
        pattern = r"===IDEAS===\n(.*?)(?=\n===|\Z)"
        match = re.search(pattern, response.content, re.DOTALL)
        
        if match:
            try:
                ideas = json.loads(match.group(1).strip())
                return ideas
            except json.JSONDecodeError:
                print("⚠️ Oracle spoke in riddles (JSON parse error).")
                return []
        
        return []

# Singleton
oracle = Oracle()
