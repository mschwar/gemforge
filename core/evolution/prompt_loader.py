import json
from pathlib import Path
from core.memory.user_taste_manager import UserTasteManager

_FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent

class PromptLoader:
    def __init__(self, agents_root: str = None):
        root = Path(agents_root).resolve() if agents_root else _FACTORY_ROOT / "agents"
        self.agents_root = root
        self.prompts_dir = self.agents_root / "prompts"
        self.taste_mgr = UserTasteManager()

    def load_active_prompt(self, agent_id: str) -> str:
        """
        Loads the active version of a prompt for a given agent.
        Logic:
        1. Look for agents/prompts/{agent_id}/metadata.json -> "active_version"
        2. Look for agents/prompts/{agent_id}/v1.md (fallback versioning)
        3. Fallback to agents/{agent_id}.md (legacy)
        """
        agent_dir = self.prompts_dir / agent_id
        prompt_content = ""

        # Strategy 1: Versioned Directory
        if agent_dir.exists() and agent_dir.is_dir():
            metadata_path = agent_dir / "metadata.json"
            active_version = "v1"
            
            if metadata_path.exists():
                try:
                    meta = json.loads(metadata_path.read_text())
                    active_version = meta.get("active_version", "v1")
                except:
                    pass
            
            version_path = agent_dir / f"{active_version}.md"
            if version_path.exists():
                prompt_content = version_path.read_text(encoding="utf-8")

        # Strategy 2: Legacy Fallback
        if not prompt_content:
            legacy_path = self.agents_root / f"{agent_id}.md"
            if legacy_path.exists():
                prompt_content = legacy_path.read_text(encoding="utf-8")
            else:
                raise FileNotFoundError(f"Could not find prompt for agent: {agent_id}")

        # Inject User Taste
        return self._inject_taste(prompt_content)

    def _inject_taste(self, content: str) -> str:
        """Appends current User Taste Memory to the prompt."""
        taste_context = self.taste_mgr.get_context_for_evolver()
        
        # Add a clear separator for the LLM
        augmented_prompt = f"{content}\n\n"
        augmented_prompt += "<!-- AUTOMATIC v2.0 TASTE INJECTION -->\n"
        augmented_prompt += f"{taste_context}\n"
        
        return augmented_prompt

# Singleton for easy access in pipeline.py
prompt_loader = PromptLoader()
