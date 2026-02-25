from typing import Any, Mapping


def read_spec_file(repo_path: str, filename: str) -> str:
    """Read a generated spec file from the project directory."""
    if not repo_path:
        return "[not available]"
    try:
        with open(f"{repo_path}/{filename}", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return f"[{filename} not yet generated]"


def build_parallel_context(state: Mapping[str, Any], extra_context: str = "") -> str:
    repo_path = str(state.get("repo_path", ""))
    return (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"UIUX_SPEC:\n{read_spec_file(repo_path, 'UIUX_SPEC.md')}\n\n"
        f"ARCHITECTURE:\n{read_spec_file(repo_path, 'ARCHITECTURE.md')}\n\n"
        f"PLATFORM: {state.get('selected_platform', 'web')}"
        f"{extra_context}"
    )


def build_ops_context(state: Mapping[str, Any]) -> str:
    repo_path = str(state.get("repo_path", ""))
    return (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"PLATFORM: {state.get('selected_platform', 'web')}\n\n"
        f"ARCHITECTURE:\n{read_spec_file(repo_path, 'ARCHITECTURE.md')}\n\n"
        f"DIRECTOR_REVIEW:\n{read_spec_file(repo_path, 'DIRECTOR_REVIEW.md')}"
    )
