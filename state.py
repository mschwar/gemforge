from typing import TypedDict, Annotated, List, Dict, Any
import operator
from datetime import datetime
from core.discipline.enforcer import DisciplineEnforcer, discipline_step

class PipelineState(TypedDict):
    """This is the single source of truth that travels through every agent."""

    # Run context
    run_id: str

    # Input from user
    raw_idea: str
    source_docs_path: str | None

    # After Document Auditor
    audited_context: str | None

    # After Vision Polisher
    polished_vision: str
    vision_approved: bool
    human_feedback: str | None

    # After Ruthless Interrogator
    canonical_docs: Dict[str, str]  # keys: MASTERBRIEF, PRD, APP_FLOW, etc.

    # After Bootstrapper
    repo_path: str
    repo_created: bool

    # After Platform Decision
    selected_platform: str
    selected_template: str
    platform_manifest: Dict[str, Any]

    # Current progress
    current_phase: str
    progress_log: Annotated[List[str], operator.add]  # merge-safe for parallel nodes
    approval_status: str  # "pending", "approved", "rejected"

    # Later stages
    architecture_complete: bool
    business_strategy_complete: bool
    landing_page_complete: bool
    frontend_complete: bool
    backend_complete: bool
    data_complete: bool
    qa_complete: bool
    director_approved: bool
    director_rejection_count: int  # tracks repeated rejections for manual intervention alerts
    infra_complete: bool
    cicd_complete: bool
    sre_complete: bool
    deploy_complete: bool

    # Final output
    live_url: str | None
    deploy_status: str | None
    shipping_complete: bool
    pipeline_status: str  # "in_progress", "success", "partial", "blocked"
    error_code: str | None
    error_stage: str | None
    operator_action: str | None

    # QA / Testing Layer (Module 2)
    tests_generated: bool
    tests_passed: bool
    test_report: str

    # Version Control (Module 3)
    git_published: bool
    git_repo_url: str
    pr_url: str

    # Cost Tracking (Module 5)
    total_tokens: int
    total_cost: float

    # Budget & Protection
    max_tokens: int
    max_cost_usd: float

    # Agentic Repair (Blueprint 02)
    repair_count: int
    repair_history: List[Dict[str, Any]]
    repair_status: str | None # "succeeded", "failed", "max_attempts_reached"

    # === DISCIPLINE PROTOCOL INTEGRATION ===
    discipline_enforced: bool
    last_audit_timestamp: str | None
    protocol_version: str

def create_initial_pipeline_state(raw_idea: str, source_docs_path: str | None = None) -> PipelineState:
    """Disciplined factory — always used instead of manual dicts."""
    # Create run_id from raw_idea for traceability
    run_id = f"gem-{raw_idea[:60].replace(' ', '-').replace('/', '')}"
    
    with discipline_step(5, "StateInit", f"Create disciplined initial state for run: {run_id}"):
        enforcer = DisciplineEnforcer()
        state: PipelineState = {
            "run_id": run_id,
            "raw_idea": raw_idea,
            "source_docs_path": source_docs_path,
            "audited_context": None,
            "polished_vision": "",
            "vision_approved": False,
            "human_feedback": None,
            "canonical_docs": {},
            "repo_path": "",
            "repo_created": False,
            "selected_platform": "",
            "selected_template": "",
            "platform_manifest": {},
            "current_phase": "vision",
            "progress_log": [],
            "approval_status": "pending",
            "architecture_complete": False,
            "business_strategy_complete": False,
            "landing_page_complete": False,
            "frontend_complete": False,
            "backend_complete": False,
            "data_complete": False,
            "qa_complete": False,
            "director_approved": False,
            "director_rejection_count": 0,
            "infra_complete": False,
            "cicd_complete": False,
            "sre_complete": False,
            "deploy_complete": False,
            "live_url": None,
            "deploy_status": None,
            "shipping_complete": False,
            "pipeline_status": "in_progress",
            "error_code": None,
            "error_stage": None,
            "operator_action": None,
            "tests_generated": False,
            "tests_passed": False,
            "test_report": "",
            "git_published": False,
            "git_repo_url": "",
            "pr_url": "",
            "total_tokens": 0,
            "total_cost": 0.0,
            # Discipline fields
            "discipline_enforced": True,
            "last_audit_timestamp": enforcer.timestamp(),
            "protocol_version": "v1.0",
            # Budget
            "max_tokens": 1_000_000,
            "max_cost_usd": 50.0,
            # Repair
            "repair_count": 0,
            "repair_history": [],
            "repair_status": None
        }
        enforcer.log_audit(f"Initial PipelineState created for thread {raw_idea[:30]}...")
        return state

if __name__ == "__main__":
    print("PipelineState ready with DisciplineEnforcer integration")
