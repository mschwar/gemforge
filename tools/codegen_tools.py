from tools.file_tools import write_file, ensure_dir
from pathlib import Path


def generate_swiftui_file(repo_path: str, filename: str, content: str) -> str:
    """Write a Swift source file into Sources/ inside the project."""
    full_path = f"{repo_path}/Sources/{filename}"
    ensure_dir(str(Path(full_path).parent))
    write_file(full_path, content)
    return full_path


def generate_platform_manifest(repo_path: str, content: str) -> str:
    path = f"{repo_path}/PLATFORM_MANIFEST.md"
    write_file(path, content)
    return path


def generate_web_file(repo_path: str, relative_path: str, content: str) -> str:
    """Write a web source file (JS/TS/CSS/HTML) into the project."""
    full_path = f"{repo_path}/{relative_path}"
    ensure_dir(str(Path(full_path).parent))
    write_file(full_path, content)
    return full_path
