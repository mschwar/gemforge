from typing import Any, Mapping

from tools.deploy_tools import is_native_mobile


def route_after_review_state(state: Mapping[str, Any]) -> str:
    return "ruthless_interrogator" if state.get("approval_status") == "approved" else "vision_polisher"


def route_after_git_publish_state(state: Mapping[str, Any]) -> str:
    return "shipping" if state.get("git_published", False) else "end"


def build_deploy_result(
    state: Mapping[str, Any],
    repo_path: str,
    selected_platform: str,
    live_url: str | None,
) -> dict[str, Any]:
    if live_url:
        return {
            "live_url": live_url,
            "deploy_complete": True,
            "deploy_status": "live",
            "pipeline_status": state.get("pipeline_status", "success"),
            "progress_log": [f"LIVE at {live_url}"],
        }

    if is_native_mobile(selected_platform):
        return {
            "live_url": None,
            "deploy_complete": True,
            "deploy_status": "local",
            "pipeline_status": state.get("pipeline_status", "success"),
            "progress_log": [f"Native project ready locally: {repo_path}"],
        }

    return {
        "live_url": None,
        "deploy_complete": True,
        "deploy_status": "failed",
        "pipeline_status": "partial",
        "error_code": "DEPLOY_FAILED",
        "error_stage": "deploy",
        "operator_action": "Run `npx vercel --prod --yes` from the generated project directory.",
        "progress_log": [f"Deploy failed; project remains local at: {repo_path}"],
    }


def build_missing_repo_publish_result() -> dict[str, Any]:
    return {
        "git_published": False,
        "pipeline_status": "blocked",
        "error_code": "REPO_PATH_MISSING",
        "error_stage": "git_publish",
        "operator_action": "Ensure bootstrapper produced a repo_path before publishing.",
        "progress_log": ["Git publish blocked (no repo_path available)"],
    }


def build_git_publish_result(
    state: Mapping[str, Any],
    publish_result: Mapping[str, Any],
) -> dict[str, Any]:
    if not publish_result.get("success", False):
        return {
            "git_published": False,
            "git_repo_url": publish_result.get("repo_url", ""),
            "pr_url": publish_result.get("pr_url", ""),
            "pipeline_status": "blocked",
            "error_code": publish_result.get("error_code", "GIT_PUBLISH_FAILED"),
            "error_stage": publish_result.get("error_stage", "git_publish"),
            "operator_action": publish_result.get(
                "operator_action",
                "Authenticate GitHub CLI and rerun publish.",
            ),
            "progress_log": [f"Git publish blocked: {publish_result.get('error', 'unknown error')}"],
        }

    return {
        "git_published": True,
        "git_repo_url": publish_result.get("repo_url", ""),
        "pr_url": publish_result.get("pr_url", ""),
        "pipeline_status": state.get("pipeline_status", "success"),
        "progress_log": [f"GitHub published: {publish_result.get('repo_url', 'N/A')}"],
    }
