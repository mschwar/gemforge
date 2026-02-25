import os
from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from core.runtime.sandbox import ProjectSandbox
from core.runtime.errors import handle_io_error
from state import PipelineState
from .utils import _index_files, parse_and_save_docs

def landing_page_node(state: PipelineState):
    print("🔨 5d. Landing Page Agent running...")
    prompt = load_prompt("24_landing_page_generator.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    
    strategy_path = f"{repo_path}/BUSINESS_STRATEGY.md"
    strategy_content = ""
    if os.path.exists(strategy_path):
        with open(strategy_path) as f:
            strategy_content = f.read()

    context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"BUSINESS_STRATEGY:\n{strategy_content}\n"
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=context)]
    response = cost_aware_invoke(messages)
    
    if repo_path:
        try:
            saved, saved_paths = parse_and_save_docs(response.content, sandbox)
            if not saved:
                 try:
                     p = sandbox.safe_write("LANDING_PAGE.html", response.content)
                     saved_paths = [p]
                 except PermissionError as e:
                     return handle_io_error(state, e, "landing page (direct save)")
            print("   → LANDING_PAGE.html saved")
            _index_files(state["run_id"], gem_name, saved_paths, "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "landing page")
        
    return {"landing_page_complete": True, "progress_log": ["✅ Landing page complete"]}
