import os
from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from core.runtime.sandbox import ProjectSandbox
from core.runtime.errors import handle_io_error
from state import PipelineState
from .utils import _index_files

def architecture_node(state: PipelineState):
    print("🔨 5. Architecture Agent running...")
    prompt = load_prompt("05_architecture.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"STAFF_AUDIT:\n{state.get('audited_context', 'N/A')}\n\n"
        + "\n".join(f"{k}: {v}" for k, v in state.get("canonical_docs", {}).items() if not k.startswith("_"))
    )
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Project context:\n\n{context}")]
    response = cost_aware_invoke(messages)
    if repo_path:
        try:
            p = sandbox.safe_write("ARCHITECTURE.md", response.content)
            print("   → ARCHITECTURE.md saved")
            _index_files(state["run_id"], gem_name, [p], "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "architecture")
    return {"architecture_complete": True, "progress_log": ["✅ Architecture complete"]}
