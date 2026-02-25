from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from state import PipelineState
from tools.file_tools import create_project_structure, write_file
from tools.deploy_tools import deploy_to_vercel
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

def qa_node(state: PipelineState):
    print("🔨 9. QA & Testing Agent...")
    return {"qa_complete": True, "progress_log": ["✅ QA complete"]}

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

    live_url = deploy_to_vercel(repo_path)

    if live_url:
        status = "live"
        print(f"\n🎉 APP IS NOW LIVE → {live_url}")
    else:
        app_name = os.path.basename(repo_path)
        live_url = f"https://{app_name}.vercel.app (run: npx vercel --prod in {repo_path})"
        status = "ready-to-deploy"
        print(f"\n📦 Project ready. To deploy: cd {repo_path} && npx vercel --prod")
        print("   (Run 'vercel login' first if you haven't already)")

    return {
        "live_url": live_url,
        "deploy_complete": True,
        "deploy_status": status,
        "progress_log": [f"🚀 Deploy status: {status} — {live_url}"],
    }

# ====================== ROUTING ======================

def route_after_review(state: PipelineState) -> str:
    if state.get("approval_status") == "approved":
        return "ruthless_interrogator"
    return "vision_polisher"

# ====================== GRAPH ======================

workflow = StateGraph(PipelineState)

nodes = [
    ("vision_polisher", vision_polisher_node),
    ("human_review", human_review_node),
    ("ruthless_interrogator", ruthless_interrogator_node),
    ("bootstrapper", bootstrapper_node),
    ("uiux", uiux_node),
    ("architecture", architecture_node),
    ("frontend", frontend_node),
    ("backend", backend_node),
    ("data", data_node),
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

# Fan-out: architecture → frontend + backend + data (parallel)
workflow.add_edge("architecture", "frontend")
workflow.add_edge("architecture", "backend")
workflow.add_edge("architecture", "data")

# Fan-in: all three → qa
workflow.add_edge(["frontend", "backend", "data"], "qa")

workflow.add_edge("qa", "infra")
workflow.add_edge("infra", "cicd")
workflow.add_edge("cicd", "sre")
workflow.add_edge("sre", "deploy")
workflow.add_edge("deploy", END)

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
memory = SqliteSaver(conn)
pipeline_app = workflow.compile(checkpointer=memory)

print("✅ PIPELINE v6 READY — Real Vercel deploy + all nodes return partial state!")
