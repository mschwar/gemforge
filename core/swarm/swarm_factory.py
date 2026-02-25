import hashlib
import os
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from core.llm import cost_aware_invoke, load_prompt
from tools.file_tools import write_file


class SwarmFactory:
    def __init__(self):
        # Temporary agents live in agents/temporary/
        # They are not committed by default unless promoted.
        self.temp_agents_dir = Path("agents/temporary")
        self.temp_agents_dir.mkdir(parents=True, exist_ok=True)

    def spawn_specialist(self, mission: str, project_context: str) -> str:
        """
        Generates a specialist agent prompt based on the mission.
        Returns the path to the generated prompt file.
        """
        print(f"🐝 Swarm Factory: Spawning specialist for mission: '{mission[:50]}...'")
        
        # 1. Use the Swarm Commander (Agent 25) to design the specialist
        # We use load_prompt from pipeline which uses prompt_loader (v2.0)
        generator_prompt = load_prompt("25_swarm_specialist_generator.md")
        
        user_content = f"MISSION: {mission}\n\nCONTEXT (Snippet): {project_context[:2000]}..."
        
        messages = [
            SystemMessage(content=generator_prompt),
            HumanMessage(content=user_content)
        ]
        
        response = cost_aware_invoke(messages)
        
        # 2. Extract the prompt content
        pattern = r"===SPECIALIST_PROMPT\.md===\n(.*?)(?=\n===|\Z)"
        match = re.search(pattern, response.content, re.DOTALL)
        
        if match:
            prompt_content = match.group(1).strip()
        else:
            # Fallback: assume the whole response is the prompt if format missed
            prompt_content = response.content
            
        # 3. Save the prompt to a temporary file
        mission_hash = hashlib.md5(mission.encode()).hexdigest()[:8]
        filename = f"specialist_{mission_hash}.md"
        file_path = self.temp_agents_dir / filename
        
        write_file(str(file_path), prompt_content)
        print(f"   → Specialist born: {file_path}")
        
        return str(file_path)

    def run_specialist(self, prompt_path: str, context: str, mission: str):
        """
        Executes the specialist agent using the generated prompt.
        """
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Specialist prompt not found: {prompt_path}")
            
        with open(prompt_path, encoding="utf-8") as f:
            system_prompt = f.read()
            
        print("🐝 Specialist Agent running...")
        
        user_input = f"""
MISSION: {mission}

FULL CONTEXT:
{context}

Execute the mission. Output all necessary file changes.
"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input)
        ]
        
        response = cost_aware_invoke(messages)
        return response.content

# Singleton
swarm_factory = SwarmFactory()
