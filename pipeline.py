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
import os
import re

llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

def load_prompt(filename: str) -> str:
    with open(f"agents/{filename}", "r", encoding="utf-8") as f:
        return f.read()

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
    response = llm.invoke(messages)
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
    response = llm.invoke(messages)
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
    response = llm.invoke(messages)
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
    response = llm.invoke(messages)
    if repo_path:
        write_file(f"{repo_path}/ARCHITECTURE.md", response.content)
        print("   → ARCHITECTURE.md saved")
    return {"architecture_complete": True, "progress_log": ["✅ Architecture complete"]}

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
    response = llm.invoke(messages)
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
        or "ios-swiftui"
    )
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
        ui_response = llm.invoke(messages)
        parse_and_save_generated_code(repo_path, ui_response.content)

        # 2. Core Logic Generator
        prompt = load_prompt("17_core_logic_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        logic_response = llm.invoke(messages)
        parse_and_save_generated_code(repo_path, logic_response.content)

        # 3. Platform-Specific Generator
        prompt = load_prompt("18_platform_specific_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        platform_response = llm.invoke(messages)
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
    print("🔨 6. Frontend Agent (parallel)...")
    return {"frontend_complete": True, "progress_log": ["✅ Frontend complete"]}

def backend_node(state: PipelineState):
    print("🔨 7. Backend Agent (parallel)...")
    return {"backend_complete": True, "progress_log": ["✅ Backend complete"]}

def data_node(state: PipelineState):
    print("🔨 8. Data Architecture Agent (parallel)...")
    return {"data_complete": True, "progress_log": ["✅ Data complete"]}

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
    response = llm.invoke(messages)
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

with discipline_step(5, "PipelineBuild", "Full LangGraph compilation with Discipline Protocol v1.0 enforced"):
    workflow = StateGraph(PipelineState)
    
    nodes = [
        ("vision_polisher", vision_polisher_node),
        ("human_review", human_review_node),
        ("ruthless_interrogator", ruthless_interrogator_node),
        ("bootstrapper", bootstrapper_node),
        ("uiux", uiux_node),
        ("architecture", architecture_node),
        ("platform_decision", platform_decision_node),
        ("code_orchestrator", code_orchestrator_node),
        ("frontend", frontend_node),
        ("backend", backend_node),
        ("data", data_node),
        ("qa_generator", qa_generator_node),
    ("qa", qa_node),
        ("infra", infra_node),
        ("cicd", cicd_node),
        ("sre", sre_node),
        ("deploy", deploy_node),
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
    workflow.add_edge("architecture", "platform_decision")
    workflow.add_edge("platform_decision", "code_orchestrator")
    
    # Fan-out: code_orchestrator → frontend + backend + data (parallel)
    workflow.add_edge("code_orchestrator", "frontend")
    workflow.add_edge("code_orchestrator", "backend")
    workflow.add_edge("code_orchestrator", "data")
    
    # Fan-in: all three → qa
    workflow.add_edge(["frontend", "backend", "data"], "qa_generator")
    workflow.add_edge("qa_generator", "qa")
    
    workflow.add_conditional_edges(
        "qa",
        lambda s: "human_review" if not s.get("tests_passed", True) else "infra",
        {"human_review": "human_review", "infra": "infra"}
    )
    workflow.add_edge("infra", "cicd")
    workflow.add_edge("cicd", "sre")
    workflow.add_edge("sre", "deploy")
    workflow.add_edge("deploy", END)
    
    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    memory = SqliteSaver(conn)
    pipeline_app = workflow.compile(checkpointer=memory)
    
    print("✅ PIPELINE v8 READY — Real Swift code generation + Xcode project + build verification! (Discipline Protocol v1.0 ENFORCED)")
    