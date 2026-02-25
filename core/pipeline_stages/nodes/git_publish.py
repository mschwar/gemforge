from core.pipeline_stages.failure_semantics import build_git_publish_result, build_missing_repo_publish_result
from tools.git_tools import push_to_github
from state import PipelineState

def git_publish_node(state: PipelineState):
    """20_git_publish.md — auto GitHub repo + push + PR"""
    print("📤 21. Git Publish running...")
    if not state.get("repo_path"):
        return build_missing_repo_publish_result()
    publish_result = push_to_github(state["repo_path"], state["raw_idea"])
    return build_git_publish_result(state, publish_result)
