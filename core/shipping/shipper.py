from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from core.llm import cost_aware_invoke, load_prompt
from tools.file_tools import write_file


class Shipper:
    def __init__(self, projects_root: str = None):
        if not projects_root:
            from tools.file_tools import PROJECTS_ROOT
            self.projects_root = PROJECTS_ROOT
        else:
            self.projects_root = Path(projects_root)

    def prepare_launch_manifest(self, project_path: str, vision: str, strategy: str, platform: str) -> str:
        """
        Generates the SHIPPING_MANIFEST.md for the project.
        """
        print(f"🚀 Launchpad: Preparing shipping manifest for {Path(project_path).name}...")
        
        prompt = load_prompt("26_shipping_manifest_agent.md")
        
        context = (
            f"POLISHED_VISION:\n{vision}\n\n"
            f"BUSINESS_STRATEGY:\n{strategy}\n\n"
            f"PLATFORM: {platform}\n"
        )
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=context)
        ]
        
        response = cost_aware_invoke(messages)
        
        # Save to project
        manifest_path = Path(project_path) / "SHIPPING_MANIFEST.md"
        write_file(str(manifest_path), response.content)
        print(f"   → SHIPPING_MANIFEST.md saved at {manifest_path}")
        
        return response.content

# Singleton
shipper = Shipper()
