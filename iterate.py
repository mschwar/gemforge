import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from core.evolution.iterator import IterationEngine
from core.llm import cost_aware_invoke
from langchain_core.messages import SystemMessage, HumanMessage
from tools.executor_tools import parse_and_save_generated_code

def main():
    if len(sys.argv) < 3:
        print("Usage: python iterate.py <project_name_folder> \"Refinement request\"")
        sys.exit(1)

    project_folder_name = sys.argv[1]
    request = sys.argv[2]
    
    from tools.file_tools import PROJECTS_ROOT
    project_path = PROJECTS_ROOT / project_folder_name
    
    if not project_path.exists():
        print(f"Error: Project folder {project_folder_name} not found in {PROJECTS_ROOT}")
        sys.exit(1)

    print(f"\n{'═'*80}")
    print(f" 🔧 GEMFORGE SURGEON — Iterating on {project_folder_name}")
    print(f"{'═'*80}\n")
    
    engine = IterationEngine()
    sys_prompt, user_prompt = engine.prepare_iteration_prompt(project_folder_name, request)
    
    messages = [SystemMessage(content=sys_prompt), HumanMessage(content=user_prompt)]
    
    print("🚀 Surgeon is analyzing codebase and performing surgery (LLM call)...")
    response = cost_aware_invoke(messages)
    
    print("\n📝 Applying changes to codebase...")
    # Use standard GemForge parser to write the files back
    count = parse_and_save_generated_code(str(project_path), response.content)
    
    print(f"\n✅ Iteration complete. {count} files updated.")
    print(f"👉 Path: {project_path}")
    print(f"{'═'*80}")

if __name__ == "__main__":
    main()
