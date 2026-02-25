import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from core.swarm.swarm_factory import swarm_factory
from core.evolution.iterator import IterationEngine
from tools.executor_tools import parse_and_save_generated_code

def main():
    if len(sys.argv) < 3:
        print("Usage: python spawn_agent.py <project_folder> \"Mission description\"")
        sys.exit(1)

    project_folder_name = sys.argv[1]
    mission = sys.argv[2]
    
    from tools.file_tools import PROJECTS_ROOT
    project_path = PROJECTS_ROOT / project_folder_name
    
    if not project_path.exists():
        print(f"Error: Project folder {project_folder_name} not found in {PROJECTS_ROOT}")
        sys.exit(1)

    print(f"\n{'═'*80}")
    print(f" 🐝 GEMFORGE SWARM — Spawning Specialist Agent for {project_folder_name}")
    print(f"    Mission: {mission[:50]}...")
    print(f"{'═'*80}\n")
    
    # 1. Gather context
    engine = IterationEngine()
    context = engine.get_project_context(project_folder_name)
    
    # 2. Spawn Agent
    prompt_path = swarm_factory.spawn_specialist(mission, context)
    
    # 3. Run Agent
    response = swarm_factory.run_specialist(prompt_path, context, mission)
    
    # 4. Apply Changes
    print("\n📝 Applying specialist output...")
    count = parse_and_save_generated_code(str(project_path), response)
    
    print(f"\n✅ Swarm mission complete. {count} files updated.")
    print(f"👉 Path: {project_path}")
    print(f"{'═'*80}")

if __name__ == "__main__":
    main()
