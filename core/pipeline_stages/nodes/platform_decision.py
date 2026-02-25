from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from core.runtime.sandbox import ProjectSandbox
from core.runtime.errors import handle_io_error
from tools.project_tools import parse_platform_manifest
from state import PipelineState
from .utils import _index_files

def platform_decision_node(state: PipelineState):
    print("🔨 5b. Platform Decision Agent running...")
    prompt = load_prompt("05b_platform_decision.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    polished_vision = state.get("polished_vision", "")
    arch_content = ""
    try:
        import os
        arch_path = f"{repo_path}/ARCHITECTURE.md"
        with open(arch_path, encoding="utf-8") as f:
            arch_content = f.read()
    except Exception:
        pass
    context = f"POLISHED_VISION:\n{polished_vision}\n\nARCHITECTURE:\n{arch_content}"
    messages = [SystemMessage(content=prompt), HumanMessage(content=context)]
    response = cost_aware_invoke(messages)
    manifest_data = parse_platform_manifest(response.content)
    if repo_path:
        try:
            p = sandbox.safe_write("PLATFORM_MANIFEST.md", response.content)
            print("   → PLATFORM_MANIFEST.md saved")
            _index_files(state["run_id"], gem_name, [p], "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "platform decision")
    return {
        "selected_platform": manifest_data.get("selected_platform", ""),
        "selected_template": manifest_data.get("template", ""),
        "platform_manifest": manifest_data,
        "progress_log": [
            "✅ Platform decision complete",
            (
                f"   ↳ platform={manifest_data.get('selected_platform', 'unknown')}, "
                f"template={manifest_data.get('template', 'unknown')}"
            ),
        ],
    }
