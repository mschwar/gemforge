from typing import TypedDict, Annotated, List, Dict, Any
import operator

class PipelineState(TypedDict):
    """This is the single source of truth that travels through every agent."""

    # Input from user
    raw_idea: str

    # After Vision Polisher
    polished_vision: str
    vision_approved: bool
    human_feedback: str | None

    # After Ruthless Interrogator
    canonical_docs: Dict[str, str]          # keys: MASTERBRIEF, PRD, APP_FLOW, etc.

    # After Bootstrapper
    repo_path: str
    repo_created: bool

    # Current progress
    current_phase: str
    progress_log: Annotated[List[str], operator.add]  # merge-safe for parallel nodes
    approval_status: str                    # "pending", "approved", "rejected"

    # Later stages
    architecture_complete: bool
    frontend_complete: bool
    backend_complete: bool
    data_complete: bool
    qa_complete: bool
    infra_complete: bool
    cicd_complete: bool
    sre_complete: bool
    deploy_complete: bool

    # Final output
    live_url: str | None
    deploy_status: str | None
