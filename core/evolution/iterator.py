import os
from pathlib import Path
from core.evolution.prompt_loader import prompt_loader

class IterationEngine:
    def __init__(self, projects_root: str = None):
        if not projects_root:
            from tools.file_tools import PROJECTS_ROOT
            self.projects_root = PROJECTS_ROOT
        else:
            self.projects_root = Path(projects_root)

    def get_project_context(self, project_name: str) -> str:
        """Reads the source code of the project to provide context for the Surgeon."""
        project_path = self.projects_root / project_name
        if not project_path.exists():
            return "Project not found."

        context = []
        # We focus on source files primarily
        extensions = {".swift", ".tsx", ".ts", ".js", ".py", ".dart", ".kt", ".md"}
        
        for root, dirs, files in os.walk(str(project_path)):
            if "node_modules" in root or ".git" in root or "__pycache__" in root:
                continue
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    rel_path = os.path.relpath(os.path.join(root, file), str(project_path))
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                            content = f.read()
                        context.append(f"===FILE: {rel_path}===\n{content}\n")
                    except:
                        pass
        
        return "\n".join(context)

    def prepare_iteration_prompt(self, project_name: str, request: str):
        # We use the prompt_loader which also injects USER TASTE (Pillar 1+8)
        prompt = prompt_loader.load_active_prompt("22_iteration_surgeon")
        context = self.get_project_context(project_name)
        
        user_prompt = f"""
PROJECT: {project_name}
REFINEMENT_REQUEST: {request}

CURRENT_CODEBASE:
{context}

Please perform the surgery now.
"""
        return prompt, user_prompt
