import os
import re
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


def _tokenize_idea(raw_idea: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", raw_idea.lower()) if len(token) >= 3}


def _score_file(relative_path: Path, idea_tokens: set[str]) -> int:
    rel = str(relative_path).lower()
    name = relative_path.name.lower()
    suffix = relative_path.suffix.lower()

    score = 0

    # Prefer docs/config and common architecture/design artifacts.
    if suffix in {".md", ".yml", ".yaml", ".json"}:
        score += 4
    if any(marker in rel for marker in ("readme", "architecture", "prd", "spec", "design", "docs")):
        score += 6
    if any(marker in rel for marker in ("main.", "app.", "index.", "src/")):
        score += 2

    # Prioritize idea-relevant filenames.
    for token in idea_tokens:
        if token in name:
            score += 10
        elif token in rel:
            score += 5

    return score


def _estimate_tokens(char_count: int) -> int:
    # Coarse approximation for planning/budget telemetry.
    return max(1, char_count // 4) if char_count > 0 else 0


def _budget(value: int | None, env_key: str, fallback: int) -> int:
    if value is not None:
        return max(1, int(value))
    return max(1, int(os.getenv(env_key, str(fallback))))


def bundle_context(
    root_path: str,
    raw_idea: str = "",
    max_file_size: int = 15000,
    max_files: int | None = None,
    max_total_chars: int | None = None,
    max_total_bytes: int | None = None,
    include_stats: bool = False,
):
    """
    Bundles high-signal files into a single XML-tagged string with hard budgets.

    Budgets can be overridden by args or env vars:
    - GEMFORGE_CONTEXT_MAX_FILES (default 40)
    - GEMFORGE_CONTEXT_MAX_CHARS (default 180000)
    - GEMFORGE_CONTEXT_MAX_BYTES (default 400000)
    """
    root = Path(root_path).resolve()
    files = get_high_signal_files(root_path)
    idea_tokens = _tokenize_idea(raw_idea)

    max_files_budget = _budget(max_files, "GEMFORGE_CONTEXT_MAX_FILES", 40)
    max_chars_budget = _budget(max_total_chars, "GEMFORGE_CONTEXT_MAX_CHARS", 180000)
    max_bytes_budget = _budget(max_total_bytes, "GEMFORGE_CONTEXT_MAX_BYTES", 400000)

    ranked_files = sorted(
        files,
        key=lambda path: (-_score_file(path.relative_to(root), idea_tokens), str(path.relative_to(root))),
    )

    bundle = [f"<directory_context path='{root}'>"]

    stats = {
        "total_files_considered": len(files),
        "included_files": 0,
        "dropped_by_budget": 0,
        "dropped_oversized_file": 0,
        "truncated_files": 0,
        "total_chars": 0,
        "total_bytes": 0,
        "estimated_tokens": 0,
        "max_files_budget": max_files_budget,
        "max_chars_budget": max_chars_budget,
        "max_bytes_budget": max_bytes_budget,
        "included_paths": [],
    }

    for f in ranked_files:
        try:
            relative_path = f.relative_to(root)

            if stats["included_files"] >= max_files_budget:
                stats["dropped_by_budget"] += 1
                continue

            # Skip very large files entirely.
            if f.stat().st_size > 1000000:
                stats["dropped_oversized_file"] += 1
                continue

            content = f.read_text(encoding="utf-8", errors="ignore")

            if len(content) > max_file_size:
                content = content[:max_file_size] + f"\n\n[... TRUNCATED DUE TO SIZE (Total: {len(content)} chars) ...]"
                stats["truncated_files"] += 1

            content_chars = len(content)
            content_bytes = len(content.encode("utf-8"))

            if (
                stats["total_chars"] + content_chars > max_chars_budget
                or stats["total_bytes"] + content_bytes > max_bytes_budget
            ):
                stats["dropped_by_budget"] += 1
                continue

            bundle.append(f"<file path='{relative_path}'>\n{content}\n</file>")
            stats["included_files"] += 1
            stats["total_chars"] += content_chars
            stats["total_bytes"] += content_bytes
            stats["included_paths"].append(str(relative_path))
        except Exception as e:
            bundle.append(f"<file path='{f}'>\n[ERROR READING FILE: {e}]\n</file>")

    bundle.append("</directory_context>")
    stats["estimated_tokens"] = _estimate_tokens(stats["total_chars"])

    output = "\n".join(bundle)
    if include_stats:
        return output, stats
    return output
