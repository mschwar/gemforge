import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from core.pipeline_stages.failure_semantics import (
    route_after_git_publish_state,
    route_after_review_state,
)
from state import PipelineState
from core.repair.agentic_loop import repair_node
from core.runtime.nodes import logged_node
from core.runtime.logging import setup_logging

# Import modularized nodes (Remediation F02)
from core.pipeline_stages.nodes.document_auditor import document_auditor_node
from core.pipeline_stages.nodes.vision_polisher import vision_polisher_node
from core.pipeline_stages.nodes.human_review import human_review_node
from core.pipeline_stages.nodes.ruthless_interrogator import ruthless_interrogator_node
from core.pipeline_stages.nodes.bootstrapper import bootstrapper_node
from core.pipeline_stages.nodes.uiux import uiux_node
from core.pipeline_stages.nodes.architecture import architecture_node
from core.pipeline_stages.nodes.business_strategist import business_strategist_node
from core.pipeline_stages.nodes.landing_page import landing_page_node
from core.pipeline_stages.nodes.platform_decision import platform_decision_node
from core.pipeline_stages.nodes.code_orchestrator import code_orchestrator_node
from core.pipeline_stages.nodes.parallel_nodes import frontend_node, backend_node, data_node
from core.pipeline_stages.nodes.ops_nodes import infra_node, cicd_node, sre_node
from core.pipeline_stages.nodes.deploy import deploy_node
from core.pipeline_stages.nodes.qa_nodes import qa_generator_node, qa_node, director_node
from core.pipeline_stages.nodes.git_publish import git_publish_node
from core.pipeline_stages.nodes.shipping import shipping_node
from core.pipeline_stages.nodes.weaver import weaver_node

setup_logging()

# ====================== NODES ======================

document_auditor_node = logged_node(document_auditor_node)
vision_polisher_node = logged_node(vision_polisher_node)
human_review_node = logged_node(human_review_node)
ruthless_interrogator_node = logged_node(ruthless_interrogator_node)
bootstrapper_node = logged_node(bootstrapper_node)
uiux_node = logged_node(uiux_node)
architecture_node = logged_node(architecture_node)
business_strategist_node = logged_node(business_strategist_node)
landing_page_node = logged_node(landing_page_node)
platform_decision_node = logged_node(platform_decision_node)
code_orchestrator_node = logged_node(code_orchestrator_node)
frontend_node = logged_node(frontend_node)
backend_node = logged_node(backend_node)
data_node = logged_node(data_node)
infra_node = logged_node(infra_node)
cicd_node = logged_node(cicd_node)
sre_node = logged_node(sre_node)
deploy_node = logged_node(deploy_node)
qa_generator_node = logged_node(qa_generator_node)
qa_node = logged_node(qa_node)
repair_node = logged_node(repair_node)
director_node = logged_node(director_node)
git_publish_node = logged_node(git_publish_node)
shipping_node = logged_node(shipping_node)
weaver_node = logged_node(weaver_node)

# ====================== ROUTING ======================

def route_after_review(state: PipelineState) -> str:
    return route_after_review_state(state)


def route_after_qa(state: PipelineState) -> str:
    if state.get("tests_passed", False):
        return "director"
    
    max_attempts = int(os.getenv("GEMFORGE_AUTO_REPAIR_MAX_ATTEMPTS", "3"))
    if state.get("repair_count", 0) < max_attempts:
        return "repair"
        
    return "director"


def route_after_git_publish(state: PipelineState) -> str:
    return route_after_git_publish_state(state)

# ====================== GRAPH ======================

def _build_pipeline():
    """Build and return the compiled LangGraph pipeline. Called once at entry-point startup."""
    workflow = StateGraph(PipelineState)

    nodes = [
        ("document_auditor", document_auditor_node),
        ("vision_polisher", vision_polisher_node),
        ("human_review", human_review_node),
        ("ruthless_interrogator", ruthless_interrogator_node),
        ("bootstrapper", bootstrapper_node),
        ("uiux", uiux_node),
        ("architecture", architecture_node),
        ("business_strategist", business_strategist_node),
        ("landing_page", landing_page_node),
        ("platform_decision", platform_decision_node),
        ("code_orchestrator", code_orchestrator_node),
        ("frontend", frontend_node),
        ("backend", backend_node),
        ("data", data_node),
        ("qa_generator", qa_generator_node),
        ("qa", qa_node),
        ("repair", repair_node),
        ("director", director_node),
        ("infra", infra_node),
        ("cicd", cicd_node),
        ("sre", sre_node),
        ("deploy", deploy_node),
        ("git_publish", git_publish_node),
        ("shipping", shipping_node),
        ("weaver", weaver_node),
    ]
    for name, func in nodes:
        workflow.add_node(name, func)

    workflow.set_entry_point("document_auditor")
    workflow.add_edge("document_auditor", "vision_polisher")
    workflow.add_edge("vision_polisher", "human_review")

    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        {"ruthless_interrogator": "ruthless_interrogator", "vision_polisher": "vision_polisher"},
    )

    workflow.add_edge("ruthless_interrogator", "bootstrapper")
    workflow.add_edge("bootstrapper", "uiux")
    workflow.add_edge("uiux", "architecture")
    workflow.add_edge("architecture", "business_strategist")
    workflow.add_edge("business_strategist", "landing_page")
    workflow.add_edge("landing_page", "platform_decision")
    workflow.add_edge("platform_decision", "code_orchestrator")

    # Fan-out: code_orchestrator → frontend + backend + data (parallel)
    workflow.add_edge("code_orchestrator", "frontend")
    workflow.add_edge("code_orchestrator", "backend")
    workflow.add_edge("code_orchestrator", "data")

    # Fan-in: all three → qa_generator
    workflow.add_edge(["frontend", "backend", "data"], "qa_generator")
    workflow.add_edge("qa_generator", "qa")

    workflow.add_conditional_edges(
        "qa",
        route_after_qa,
        {"director": "director", "repair": "repair"},
    )
    workflow.add_edge("repair", "qa")

    workflow.add_conditional_edges(
        "director",
        lambda s: "infra" if s.get("director_approved", False) else "human_review",
        {"human_review": "human_review", "infra": "infra"},
    )

    workflow.add_edge("infra", "cicd")
    workflow.add_edge("cicd", "sre")
    workflow.add_edge("sre", "deploy")
    workflow.add_edge("deploy", "git_publish")
    workflow.add_conditional_edges(
        "git_publish",
        route_after_git_publish,
        {"shipping": "shipping", "end": END},
    )
    workflow.add_edge("shipping", "weaver")
    workflow.add_edge("weaver", END)

    _db_path = Path(__file__).resolve().parent / "checkpoints.db"
    conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    memory = SqliteSaver(conn)
    app = workflow.compile(checkpointer=memory)
    print("✅ PIPELINE READY — GemForge multi-agent factory compiled.")
    return app


_pipeline_app = None


def get_pipeline_app():
    """Lazily compile the LangGraph pipeline on first call."""
    global _pipeline_app
    if _pipeline_app is None:
        _pipeline_app = _build_pipeline()
    return _pipeline_app
