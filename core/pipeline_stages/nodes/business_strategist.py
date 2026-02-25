from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from core.runtime.sandbox import ProjectSandbox
from core.runtime.errors import handle_io_error
from state import PipelineState
from .utils import _index_files, parse_and_save_docs

def business_strategist_node(state: PipelineState):
    print("🔨 5c. Business Strategist Agent running...")
    prompt = load_prompt("23_business_strategist.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    
    docs = state.get("canonical_docs", {})
    context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"PRD:\n{docs.get('PRD.md', 'N/A')}\n"
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=context)]
    response = cost_aware_invoke(messages)
    
    if repo_path:
        try:
            saved, saved_paths = parse_and_save_docs(response.content, sandbox)
            if not saved:
                 try:
                     p = sandbox.safe_write("BUSINESS_STRATEGY.md", response.content)
                     saved_paths = [p]
                 except PermissionError as e:
                     return handle_io_error(state, e, "business strategist (direct save)")
            print("   → BUSINESS_STRATEGY.md saved")
            _index_files(state["run_id"], gem_name, saved_paths, "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "business strategist")
        
    return {"business_strategy_complete": True, "progress_log": ["✅ Business strategy complete"]}
