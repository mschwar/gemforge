from dotenv import load_dotenv
load_dotenv()
from core.discipline.enforcer import enforce_protocol, discipline_step
from state import create_initial_pipeline_state

from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from state import PipelineState
from tools.file_tools import create_project_structure, write_file
from tools.deploy_tools import deploy_to_vercel
from tools.project_tools import (
    apply_template,
    generate_xcode_project,
    parse_platform_manifest,
)
from tools.executor_tools import run_tests
from tools.git_tools import push_to_github
from core.evolution.prompt_loader import prompt_loader
import os
import re
from pathlib import Path

llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)

def load_prompt(filename: str) -> str:
    # Support both legacy calls and new agent_ids
    agent_id = filename.replace(".md", "")
    return prompt_loader.load_active_prompt(agent_id)

def parse_and_save_docs(response_text: str, repo_path: str) -> dict:
    """Parse ===FILENAME=== blocks and write each to disk."""
    saved = {}
    pattern = r"===([^=]+\.md|[^=]+\.txt)==="
    parts = re.split(pattern, response_text)
    for i in range(1, len(parts) - 1, 2):
        filename = parts[i].strip()
        content = parts[i + 1].strip()
        write_file(f"{repo_path}/{filename}", content)
        saved[filename] = content[:200]  # store preview in state
        print(f"   → Saved {filename}")
    return saved

# ====================== NODES ======================

def vision_polisher_node(state: PipelineState):
    print("🔨 1. Vision Polisher running...")
    prompt = load_prompt("01_vision_polisher.md")
    feedback = state.get("human_feedback")
    if feedback:
        user_content = (
            f"Raw Idea: {state['raw_idea']}\n\n"
            f"Previous polished vision:\n{state['polished_vision']}\n\n"
            f"User feedback: {feedback}\n\nPlease refine the vision based on this feedback."
        )
    else:
        user_content = f"Raw Idea: {state['raw_idea']}"
    messages = [SystemMessage(content=prompt), HumanMessage(content=user_content)]
    response = cost_aware_invoke(messages)
    print("   → Polished vision ready for approval")
    return {
        "polished_vision": response.content,
        "approval_status": "pending",
        "human_feedback": None,
        "progress_log": ["✅ Vision Polisher completed"],
    }

def human_review_node(state: PipelineState):
    print("⏸️  HUMAN APPROVAL GATE — waiting for you...")
    decision = interrupt("Review the polished vision. Approve or request refinements.")
    updates = {"approval_status": decision.get("action", "pending")}
    if decision.get("feedback"):
        updates["human_feedback"] = decision["feedback"]
    return updates

def ruthless_interrogator_node(state: PipelineState):
    print("🔨 2. Ruthless Interrogator generating canonical docs...")
    prompt = load_prompt("02_ruthless_interrogator.md")
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"POLISHED_VISION:\n\n{state['polished_vision']}\n\nGenerate all canonical docs now.")
    ]
    response = cost_aware_invoke(messages)
    return {
        "canonical_docs": {"_raw_output": response.content},
        "progress_log": ["✅ Canonical docs generated"],
    }

def bootstrapper_node(state: PipelineState):
    print("🔨 3. Bootstrapper creating REAL project...")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    repo_path = create_project_structure(gem_name)

    # Write canonical docs now that the folder exists
    raw_output = state.get("canonical_docs", {}).get("_raw_output", "")
    if raw_output:
        saved = parse_and_save_docs(raw_output, repo_path)
        canonical_docs = saved if saved else {"INTERROGATION.md": raw_output[:200]}
        if not saved:
            write_file(f"{repo_path}/INTERROGATION.md", raw_output)
    else:
        canonical_docs = {}

    print(f"   → Project ready: {repo_path}")
    return {
        "repo_path": repo_path,
        "repo_created": True,
        "canonical_docs": canonical_docs,
        "progress_log": [f"✅ Repo + docs at {repo_path}"],
    }

def uiux_node(state: PipelineState):
    print("🔨 4. UI/UX Design Agent running...")
    prompt = load_prompt("04_uiux_design.md")
    repo_path = state.get("repo_path", "")
    context = state.get("polished_vision", "") + "\n\n" + "\n".join(
        f"{k}: {v}" for k, v in state.get("canonical_docs", {}).items() if not k.startswith("_")
    )
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Project context:\n\n{context}")]
    response = cost_aware_invoke(messages)
    if repo_path:
        write_file(f"{repo_path}/UIUX_SPEC.md", response.content)
        print("   → UIUX_SPEC.md saved")
    return {"progress_log": ["✅ UI/UX spec complete"]}

def architecture_node(state: PipelineState):
    print("🔨 5. Architecture Agent running...")
    prompt = load_prompt("05_architecture.md")
    repo_path = state.get("repo_path", "")
    context = state.get("polished_vision", "") + "\n\n" + "\n".join(
        f"{k}: {v}" for k, v in state.get("canonical_docs", {}).items() if not k.startswith("_")
    )
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Project context:\n\n{context}")]
    response = cost_aware_invoke(messages)
    if repo_path:
        write_file(f"{repo_path}/ARCHITECTURE.md", response.content)
        print("   → ARCHITECTURE.md saved")
    return {"architecture_complete": True, "progress_log": ["✅ Architecture complete"]}

def business_strategist_node(state: PipelineState):
    print("🔨 5c. Business Strategist Agent running...")
    prompt = load_prompt("23_business_strategist.md")
    repo_path = state.get("repo_path", "")
    
    # Context includes the primary docs for business alignment
    docs = state.get("canonical_docs", {})
    context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"PRD:\n{docs.get('PRD.md', 'N/A')}\n"
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=context)]
    response = cost_aware_invoke(messages)
    
    if repo_path:
        # Use our standard doc parser to save BUSINESS_STRATEGY.md
        saved = parse_and_save_docs(response.content, repo_path)
        if not saved:
             write_file(f"{repo_path}/BUSINESS_STRATEGY.md", response.content)
        print("   → BUSINESS_STRATEGY.md saved")
        
    return {"business_strategy_complete": True, "progress_log": ["✅ Business strategy complete"]}

def landing_page_node(state: PipelineState):
    print("🔨 5d. Landing Page Agent running...")
    prompt = load_prompt("24_landing_page_generator.md")
    repo_path = state.get("repo_path", "")
    
    # Context includes the primary docs for landing page alignment
    strategy_path = f"{repo_path}/BUSINESS_STRATEGY.md"
    strategy_content = ""
    if os.path.exists(strategy_path):
        with open(strategy_path, "r") as f:
            strategy_content = f.read()

    context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"BUSINESS_STRATEGY:\n{strategy_content}\n"
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=context)]
    response = cost_aware_invoke(messages)
    
    if repo_path:
        # Use our standard doc parser to save LANDING_PAGE.html
        saved = parse_and_save_docs(response.content, repo_path)
        if not saved:
             write_file(f"{repo_path}/LANDING_PAGE.html", response.content)
        print("   → LANDING_PAGE.html saved")
        
    return {"landing_page_complete": True, "progress_log": ["✅ Landing page complete"]}

def platform_decision_node(state: PipelineState):
    print("🔨 5b. Platform Decision Agent running...")
    prompt = load_prompt("05b_platform_decision.md")
    repo_path = state.get("repo_path", "")
    polished_vision = state.get("polished_vision", "")
    arch_content = ""
    try:
        arch_path = f"{repo_path}/ARCHITECTURE.md"
        with open(arch_path, "r", encoding="utf-8") as f:
            arch_content = f.read()
    except Exception:
        pass
    context = f"POLISHED_VISION:\n{polished_vision}\n\nARCHITECTURE:\n{arch_content}"
    messages = [SystemMessage(content=prompt), HumanMessage(content=context)]
    response = cost_aware_invoke(messages)
    manifest_data = parse_platform_manifest(response.content)
    if repo_path:
        write_file(f"{repo_path}/PLATFORM_MANIFEST.md", response.content)
        print("   → PLATFORM_MANIFEST.md saved")
    return {
        "selected_platform": manifest_data.get("selected_platform", ""),
        "selected_template": manifest_data.get("template", ""),
        "platform_manifest": manifest_data,
        "progress_log": [
            "✅ Platform decision complete",
            (
                f"   ↳ platform={manifest_data.get('selected_platform', 'unknown')}, "
                f"template={manifest_data.get('template', 'unknown')}"
            ),
        ],
    }

def code_orchestrator_node(state: PipelineState):
    print("🔨 6. Code Generation Orchestrator — launching real generators...")
    repo_path = state.get("repo_path", "")
    from tools.executor_tools import parse_and_save_generated_code, build_and_verify_xcode

    manifest_path = f"{repo_path}/PLATFORM_MANIFEST.md"
    manifest_content = ""
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as manifest_file:
            manifest_content = manifest_file.read()
    manifest_data = parse_platform_manifest(manifest_content)

    template_hint = (
        manifest_data.get("template")
        or manifest_data.get("selected_platform")
        or state.get("selected_template")
    )
    
    if not template_hint:
        raise ValueError("CRITICAL: Platform Decision Agent failed to produce a valid template selection.")

    template_result = apply_template(repo_path, template_hint)
    template_metadata = template_result.get("metadata", {})
    selected_platform = template_result.get("platform", template_hint)
    supports_llm_generators = bool(template_metadata.get("supports_llm_generators", False))

    progress = [f"✅ Template applied: {template_result.get('name')} ({selected_platform})"]

    def _safe_read(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception:
            return ""

    generator_context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"UIUX_SPEC:\n{_safe_read(f'{repo_path}/UIUX_SPEC.md')}\n\n"
        f"ARCHITECTURE:\n{_safe_read(f'{repo_path}/ARCHITECTURE.md')}\n\n"
        f"PLATFORM_MANIFEST:\n{manifest_content}"
    )

    if supports_llm_generators:
        # 1. UI Code Generator
        prompt = load_prompt("16_ui_code_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        ui_response = cost_aware_invoke(messages)
        parse_and_save_generated_code(repo_path, ui_response.content)

        # 2. Core Logic Generator
        prompt = load_prompt("17_core_logic_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        logic_response = cost_aware_invoke(messages)
        parse_and_save_generated_code(repo_path, logic_response.content)

        # 3. Platform-Specific Generator
        prompt = load_prompt("18_platform_specific_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        platform_response = cost_aware_invoke(messages)
        parse_and_save_generated_code(repo_path, platform_response.content)
        progress.append("✅ LLM code generators completed")
    else:
        progress.append("✅ Template-only code path selected (no LLM generators)")

    # 4. Project structure / build verification
    if selected_platform == "ios-swiftui":
        app_name = template_result.get("context", {}).get("APP_NAME_SAFE", "GemForgeApp")
        generate_xcode_project(repo_path, app_name)
        build_and_verify_xcode(repo_path)
        progress.append("✅ iOS project structure + build verification complete")
    else:
        validation = template_result.get("validation", {})
        if validation.get("valid", False):
            progress.append("✅ Template validation complete")
        else:
            progress.append(
                f"⚠️ Template validation missing files: {validation.get('missing_files', [])}"
            )

    return {
        "selected_platform": selected_platform,
        "selected_template": template_result.get("name"),
        "platform_manifest": manifest_data,
        "progress_log": progress,
    }

# ---- PARALLEL AGENTS (return only changed keys — required for parallel execution) ----

def frontend_node(state: PipelineState):
    print("🔨 7. Frontend Agent (parallel)...")
    prompt = load_prompt("06_frontend.md")
    repo_path = state.get("repo_path", "")
    context = f"POLISHED_VISION:\n{state['polished_vision']}\n\nARCHITECTURE:\n{state.get('architecture_complete')}"
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    if repo_path:
        write_file(f"{repo_path}/FRONTEND_SPEC.md", response.content)
    return {"frontend_complete": True, "progress_log": ["✅ Frontend spec complete"]}

def backend_node(state: PipelineState):
    print("🔨 8. Backend Agent (parallel)...")
    prompt = load_prompt("07_backend.md")
    repo_path = state.get("repo_path", "")
    context = f"POLISHED_VISION:\n{state['polished_vision']}\n\nARCHITECTURE:\n{state.get('architecture_complete')}"
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    if repo_path:
        write_file(f"{repo_path}/BACKEND_SPEC.md", response.content)
    return {"backend_complete": True, "progress_log": ["✅ Backend spec complete"]}

def data_node(state: PipelineState):
    print("🔨 9. Data Architecture Agent (parallel)...")
    prompt = load_prompt("08_data.md")
    repo_path = state.get("repo_path", "")
    context = f"POLISHED_VISION:\n{state['polished_vision']}\n\nARCHITECTURE:\n{state.get('architecture_complete')}"
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    if repo_path:
        write_file(f"{repo_path}/DATA_SPEC.md", response.content)
    return {"data_complete": True, "progress_log": ["✅ Data spec complete"]}

# ---- SEQUENTIAL CHAIN ----

def infra_node(state: PipelineState):
    print("🔨 10. Infrastructure Agent...")
    return {"infra_complete": True, "progress_log": ["✅ Infra complete"]}

def cicd_node(state: PipelineState):
    print("🔨 11. CI/CD Agent...")
    return {"cicd_complete": True, "progress_log": ["✅ CI/CD complete"]}

def sre_node(state: PipelineState):
    print("🔨 12. SRE & Observability Agent...")
    return {"sre_complete": True, "progress_log": ["✅ SRE complete"]}

def deploy_node(state: PipelineState):
    print("🔨 13. Final Deploy Agent...")
    repo_path = state.get("repo_path", "new-gem")
    idea = state.get("raw_idea", "")
    selected_platform = str(state.get("selected_platform", "")).strip().lower()

    native_platforms = {"ios-swiftui", "flutter", "react-native", "android-kotlin"}
    if selected_platform in native_platforms:
        # Force native skip even when the raw idea text does not include native keywords.
        live_url = deploy_to_vercel(repo_path, selected_platform)
    else:
        live_url = deploy_to_vercel(repo_path, idea)

    if live_url:
        print(f"\n🎉 APP IS NOW LIVE → {live_url}")
        return {
            "live_url": live_url,
            "deploy_complete": True,
            "deploy_status": "live",
            "progress_log": [f"🎉 LIVE at {live_url}"],
        }
    else:
        print(f"\n📦 Project ready locally at: {repo_path}")
        return {
            "live_url": None,
            "deploy_complete": True,
            "deploy_status": "local",
            "progress_log": [f"📦 Project ready locally: {repo_path}"],
        }

# ====================== ROUTING ======================

def route_after_review(state: PipelineState) -> str:
    if state.get("approval_status") == "approved":
        return "ruthless_interrogator"
    return "vision_polisher"

# ====================== GRAPH ======================

# ====================== QA / TESTING NODES (Module 2 — Real QA Layer) ======================
def qa_generator_node(state: PipelineState):
    """19_qa_generator.md — generates platform-appropriate tests"""
    print("🧪 19. QA Generator running...")
    prompt = load_prompt("19_qa_generator.md")
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Project at: {state['repo_path']}\nPlatform: {state['selected_platform']}\nGenerate tests now.")]
    response = cost_aware_invoke(messages)
    saved = parse_and_save_docs(response.content, state["repo_path"])
    return {
        "tests_generated": True,
        "test_report": "Tests generated — see TESTS_SUMMARY.md",
        "progress_log": [f"🧪 Generated tests for {state['selected_platform']}"]
    }

def qa_node(state: PipelineState):
    """Executes the tests via run_tests and decides pass/fail"""
    print("🧪 20. QA Executor running...")
    if not state.get("repo_path"):
        return {"tests_passed": False, "test_report": "No repo_path — skipping tests", "progress_log": ["⚠️ QA skipped (no repo)"]}
    test_result = run_tests(state["repo_path"], state["selected_platform"])
    return {
        "tests_passed": test_result["success"],
        "test_report": test_result["report"],
        "progress_log": [f"🧪 QA Result: {test_result['report']} ({test_result['failures']} failures)"]
    }


def director_node(state: PipelineState):
    print("🎬 20b. Director Review running...")
    prompt = load_prompt("13_director.md")
    repo_path = state.get("repo_path", "")
    
    def _safe_read(filename):
        try:
            with open(f"{repo_path}/{filename}", "r") as f:
                return f.read()
        except:
            return "File not found."

    context = (
        f"POLISHED_VISION:\n{state['polished_vision']}\n\n"
        f"ARCHITECTURE:\n{_safe_read('ARCHITECTURE.md')}\n\n"
        f"FRONTEND_SPEC:\n{_safe_read('FRONTEND_SPEC.md')}\n\n"
        f"BACKEND_SPEC:\n{_safe_read('BACKEND_SPEC.md')}\n\n"
        f"DATA_SPEC:\n{_safe_read('DATA_SPEC.md')}\n\n"
        f"QA_REPORT:\n{state.get('test_report', 'N/A')}"
    )
    
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    
    if repo_path:
        write_file(f"{repo_path}/DIRECTOR_REVIEW.md", response.content)
        print("   → DIRECTOR_REVIEW.md saved")
        
    is_green = "GREEN LIGHT" in response.content.upper()
    
    return {
        "director_approved": is_green,
        "progress_log": [f"🎬 Director Verdict: {'✅ GREEN LIGHT' if is_green else '⚠️ CORRECTION REQUESTED'}"]
    }


# ====================== GIT PUBLISH NODE (Module 3) ======================
def git_publish_node(state: PipelineState):
    """20_git_publish.md — auto GitHub repo + push + PR"""
    print("📤 21. Git Publish running...")
    if not state.get("repo_path"):
        return {"git_published": False, "progress_log": ["⚠️ Git publish skipped (no repo)"]}
    publish_result = push_to_github(state["repo_path"], state["raw_idea"])
    return {
        "git_published": publish_result["success"],
        "git_repo_url": publish_result.get("repo_url", ""),
        "pr_url": publish_result.get("pr_url", ""),
        "progress_log": [f"📤 GitHub published: {publish_result.get('repo_url', 'N/A')}"]
    }


def shipping_node(state: PipelineState):
    """26_shipping_manifest_agent.md — auto-generates launch metadata and checklists"""
    print("🚀 23. Shipping Manifest (v2.0) running...")
    from core.shipping.shipper import shipper as launch_shipper
    
    repo_path = state.get("repo_path")
    if not repo_path:
        return {"shipping_complete": False, "progress_log": ["⚠️ Shipping skipped (no repo)"]}
        
    vision = state.get("polished_vision", "")
    platform = state.get("selected_platform", "Web")
    
    # Try to load strategy
    strategy_path = Path(repo_path) / "BUSINESS_STRATEGY.md"
    strategy = ""
    if os.path.exists(strategy_path):
        with open(strategy_path, "r") as f:
            strategy = f.read()
            
    launch_shipper.prepare_launch_manifest(repo_path, vision, strategy, platform)
    
    return {
        "shipping_complete": True,
        "progress_log": ["🚀 Launchpad: SHIPPING_MANIFEST.md ready"]
    }


# ====================== WEAVER REFLECTION NODE (v2.0 Pillar 1+8) ======================
def weaver_node(state: PipelineState):
    """21_weaver_reflector.md — extracts lessons & updates user taste"""
    print("🕸️  22. Weaver Reflector (v2.0) running...")
    from core.evolution.weaver import parse_and_log_weaver_output
    from core.evolution.iterator import IterationEngine
    
    prompt = load_prompt("21_weaver_reflector.md")
    gem_id = state.get("raw_idea", "Unknown")[:30]
    
    # NEW: Gather actual code context so Weaver can see WHY things failed
    code_context = ""
    repo_path = state.get("repo_path")
    if repo_path and os.path.exists(repo_path):
        engine = IterationEngine()
        code_context = engine.get_project_context(Path(repo_path).name)

    # Collect context for the Weaver
    context = (
        f"RAW_IDEA: {state.get('raw_idea')}\n"
        f"POLISHED_VISION: {state.get('polished_vision')}\n"
        f"HUMAN_FEEDBACK: {state.get('human_feedback')}\n"
        f"TEST_REPORT: {state.get('test_report')}\n"
        f"GENERATED_CODE:\n{code_context[:5000]}\n" # Limit context
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Analyze this gem history:\n\n{context}")]
    response = cost_aware_invoke(messages)
    
    stats = parse_and_log_weaver_output(response.content, gem_id)
    print(f"   → Weaver complete: {stats['lessons_count']} lessons, {stats['taste_updates_count']} taste updates.")
    
    return {
        "progress_log": [f"🕸️ Weaver Reflector: {stats['lessons_count']} lessons captured"]
    }


# ====================== COST-AWARE LLM WRAPPER (Module 5) ======================
from tools.cost_tracker import cost_tracker

def cost_aware_invoke(prompt_messages):
    """Every LLM call now tracked automatically."""
    response = llm.invoke(prompt_messages)
    cost_tracker.track_call(response)
    return response

with discipline_step(5, "PipelineBuild", "Full LangGraph compilation with Discipline Protocol v1.0 enforced"):
    workflow = StateGraph(PipelineState)
    
    nodes = [
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
    
    workflow.set_entry_point("vision_polisher")
    workflow.add_edge("vision_polisher", "human_review")
    
    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        {"ruthless_interrogator": "ruthless_interrogator", "vision_polisher": "vision_polisher"}
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
    
    # Fan-in: all three → qa
    workflow.add_edge(["frontend", "backend", "data"], "qa_generator")
    workflow.add_edge("qa_generator", "qa")
    
    workflow.add_edge("qa", "director")
    
    workflow.add_conditional_edges(
        "director",
        lambda s: "infra" if s.get("director_approved", False) else "human_review",
        {"human_review": "human_review", "infra": "infra"}
    )
    
    workflow.add_edge("infra", "cicd")
    workflow.add_edge("cicd", "sre")
    workflow.add_edge("sre", "deploy")
    workflow.add_edge("deploy", "git_publish")
    workflow.add_edge("git_publish", "shipping")
    workflow.add_edge("shipping", "weaver")
    workflow.add_edge("weaver", END)
    
    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    memory = SqliteSaver(conn)
    pipeline_app = workflow.compile(checkpointer=memory)
    
    print("✅ PIPELINE v8 READY — Real Swift code generation + Xcode project + build verification! (Discipline Protocol v1.0 ENFORCED)")
    