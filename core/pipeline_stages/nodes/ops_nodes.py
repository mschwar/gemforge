from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from core.runtime.sandbox import ProjectSandbox
from core.runtime.errors import handle_io_error
from core.pipeline_stages.context_builders import build_ops_context
from state import PipelineState
from .utils import _index_files, parse_and_save_docs

def infra_node(state: PipelineState):
    print("🔨 10. Infrastructure Agent...")
    prompt = load_prompt("10_infra.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=build_ops_context(state))])
    if repo_path:
        try:
            saved, saved_paths = parse_and_save_docs(response.content, sandbox)
            if not saved:
                try:
                    p = sandbox.safe_write("INFRA.md", response.content)
                    saved_paths = [p]
                except PermissionError as e:
                    return handle_io_error(state, e, "infra (direct save)")
            print("   → Infrastructure spec saved")
            _index_files(state["run_id"], gem_name, saved_paths, "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "infra")
    return {"infra_complete": True, "progress_log": ["✅ Infra spec complete"]}

def cicd_node(state: PipelineState):
    print("🔨 11. CI/CD Agent...")
    prompt = load_prompt("11_cicd.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=build_ops_context(state))])
    if repo_path:
        try:
            saved, saved_paths = parse_and_save_docs(response.content, sandbox)
            if not saved:
                try:
                    p = sandbox.safe_write("CICD.md", response.content)
                    saved_paths = [p]
                except PermissionError as e:
                    return handle_io_error(state, e, "cicd (direct save)")
            print("   → CI/CD spec saved")
            _index_files(state["run_id"], gem_name, saved_paths, "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "cicd")
    return {"cicd_complete": True, "progress_log": ["✅ CI/CD spec complete"]}

def sre_node(state: PipelineState):
    print("🔨 12. SRE & Observability Agent...")
    prompt = load_prompt("12_sre.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    sandbox = ProjectSandbox(repo_path)
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=build_ops_context(state))])
    if repo_path:
        try:
            saved, saved_paths = parse_and_save_docs(response.content, sandbox)
            if not saved:
                try:
                    p = sandbox.safe_write("SRE.md", response.content)
                    saved_paths = [p]
                except PermissionError as e:
                    return handle_io_error(state, e, "sre (direct save)")
            print("   → SRE spec saved")
            _index_files(state["run_id"], gem_name, saved_paths, "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "sre")
    return {"sre_complete": True, "progress_log": ["✅ SRE spec complete"]}
