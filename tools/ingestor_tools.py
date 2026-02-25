import subprocess
from pathlib import Path


def get_high_signal_files(root_path: str) -> list[Path]:
    """
    Returns a list of high-signal files from the given path.
    Prioritizes git-tracked files if available, otherwise falls back to a walk.
    """
    root = Path(root_path).resolve()
    
    # 1. Try Git first
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True
        )
        files = [root / f for f in result.stdout.splitlines()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        # 2. Fallback to recursive walk
        files = []
        # Common ignored directories
        ignored_dirs = {".git", "node_modules", "__pycache__", "venv", ".venv", "build", "dist"}
        for p in root.rglob("*"):
            if p.is_file() and not any(ignored in p.parts for ignored in ignored_dirs):
                files.append(p)

    # 3. Filter for high-signal extensions
    valid_extensions = {".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".sh", ".yml", ".yaml", ".c", ".h", ".cpp", ".swift", ".kt", ".dart"}
    signal_files = [f for f in files if f.suffix.lower() in valid_extensions]
    
    return signal_files

def bundle_context(root_path: str, max_file_size: int = 15000) -> str:
    """
    Bundles the high-signal files in a directory into a single XML-tagged string.
    """
    root = Path(root_path).resolve()
    files = get_high_signal_files(root_path)
    
    bundle = [f"<directory_context path='{root}'>"]
    
    for f in files:
        try:
            relative_path = f.relative_to(root)
            # Skip very large files or binary-ish files
            if f.stat().st_size > 1000000: # 1MB limit for safety
                continue
                
            content = f.read_text(encoding="utf-8", errors="ignore")
            
            if len(content) > max_file_size:
                content = content[:max_file_size] + f"\n\n[... TRUNCATED DUE TO SIZE (Total: {len(content)} chars) ...]"
            
            bundle.append(f"<file path='{relative_path}'>\n{content}\n</file>")
        except Exception as e:
            bundle.append(f"<file path='{f}'>\n[ERROR READING FILE: {e}]\n</file>")
            
    bundle.append("</directory_context>")
    return "\n".join(bundle)
