from core.pipeline_stages.failure_semantics import build_deploy_result
from tools.deploy_tools import deploy_to_vercel
from state import PipelineState

def deploy_node(state: PipelineState):
    print("🔨 13. Final Deploy Agent...")
    repo_path = state.get("repo_path", "new-gem")
    selected_platform = str(state.get("selected_platform", "")).strip().lower()

    live_url = deploy_to_vercel(repo_path, selected_platform)

    result = build_deploy_result(state, repo_path, selected_platform, live_url)
    if result.get("deploy_status") == "live":
        print(f"\n🎉 APP IS NOW LIVE → {result.get('live_url')}")
    elif result.get("deploy_status") == "local":
        print(f"\n📦 Native project ready locally at: {repo_path}")
    else:
        print(f"\n📦 Project ready locally at: {repo_path}")
    return result
