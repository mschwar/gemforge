from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from core.runtime.sandbox import ProjectSandbox
from core.runtime.errors import handle_io_error
from core.memory.retriever import semantic_retriever
from core.pipeline_stages.context_builders import build_parallel_context
from state import PipelineState
from .utils import _index_files

def _build_parallel_context_internal(state: PipelineState) -> str:
    vision = state.get("polished_vision", "")
    rag_context = ""
    try:
        past_examples = semantic_retriever.search(vision, k=3)
        if past_examples:
            rag_context = "\n### RELEVANT PAST EXAMPLES (FOR CONTEXT):\n"
            for i, ex in enumerate(past_examples):
                rag_context += f"\n-- Example {i+1} (Project: {ex['metadata'].get('project_name', 'Unknown')}) --\n"
                rag_context += ex["text"] + "\n"
    except Exception as e:
        print(f"   ⚠️ RAG retrieval failed: {e}")
    return build_parallel_context(state, extra_context=rag_context)

def frontend_node(state: PipelineState):
    print("🔨 7. Frontend Agent (parallel)...")
    prompt = load_prompt("06_frontend.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    context = _build_parallel_context_internal(state)
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    if repo_path:
        try:
            p = sandbox.safe_write("FRONTEND_SPEC.md", response.content)
            _index_files(state["run_id"], gem_name, [p], "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "frontend")
    return {"frontend_complete": True, "progress_log": ["✅ Frontend spec complete"]}

def backend_node(state: PipelineState):
    print("🔨 8. Backend Agent (parallel)...")
    prompt = load_prompt("07_backend.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    context = _build_parallel_context_internal(state)
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    if repo_path:
        try:
            p = sandbox.safe_write("BACKEND_SPEC.md", response.content)
            _index_files(state["run_id"], gem_name, [p], "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "backend")
    return {"backend_complete": True, "progress_log": ["✅ Backend spec complete"]}

def data_node(state: PipelineState):
    print("🔨 9. Data Architecture Agent (parallel)...")
    prompt = load_prompt("08_data.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    context = _build_parallel_context_internal(state)
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    if repo_path:
        try:
            p = sandbox.safe_write("DATA_SPEC.md", response.content)
            _index_files(state["run_id"], gem_name, [p], "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "data")
    return {"data_complete": True, "progress_log": ["✅ Data spec complete"]}
