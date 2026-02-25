import os
from pathlib import Path
from typing import Union

class ProjectSandbox:
    """Enforces a root directory jail for all project-related file operations."""
    
    def __init__(self, project_root: Union[str, Path]):
        self.root = Path(project_root).resolve()
        if not self.root.exists():
            os.makedirs(self.root, exist_ok=True)

    def is_safe_path(self, path: Union[str, Path]) -> bool:
        """Checks if a path is within the project root."""
        try:
            target = (self.root / path).resolve()
            return target == self.root or self.root in target.parents
        except (ValueError, RuntimeError):
            return False

    def safe_write(self, rel_path: str, content: str) -> Path:
        """Writes content to a file, ensuring it's within the sandbox."""
        target = (self.root / rel_path).resolve()
        
        # Security Check
        try:
            target.relative_to(self.root)
        except ValueError:
            raise PermissionError(f"SANDBOX VIOLATION: Attempted to write outside root: {rel_path}")

        # Ensure directory exists
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
            
        return target

    def safe_read(self, rel_path: str) -> str:
        """Reads a file from the sandbox."""
        target = (self.root / rel_path).resolve()
        
        try:
            target.relative_to(self.root)
        except ValueError:
            raise PermissionError(f"SANDBOX VIOLATION: Attempted to read outside root: {rel_path}")
            
        if not target.exists():
            return ""
            
        return target.read_text(encoding="utf-8")
