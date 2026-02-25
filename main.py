from dotenv import load_dotenv
load_dotenv()
from pipeline import pipeline_app
from state import PipelineState
import sys

if len(sys.argv) < 2:
    print("Usage: python main.py \"Your raw idea\"")
    sys.exit(1)

raw_idea = sys.argv[1]
thread_id = "gem-" + raw_idea[:40].replace(" ", "-").replace("/", "")
config = {"configurable": {"thread_id": thread_id}}

# Save thread_id so resume.py can find this session automatically
with open(".thread_id", "w") as f:
    f.write(thread_id)

initial_state: PipelineState = {
    "raw_idea": raw_idea,
    "polished_vision": "",
    "vision_approved": False,
    "human_feedback": None,
    "canonical_docs": {},
    "repo_path": "",
    "repo_created": False,
    "current_phase": "vision",
    "progress_log": [],
    "approval_status": "pending",
    "architecture_complete": False,
    "frontend_complete": False,
    "backend_complete": False,
    "data_complete": False,
    "qa_complete": False,
    "infra_complete": False,
    "cicd_complete": False,
    "sre_complete": False,
    "deploy_complete": False,
    "live_url": None,
    "deploy_status": None
}

print(f"🚀 Starting GemForge")
print(f"   Thread ID: {thread_id}")
print(f"   Idea: {raw_idea[:80]}")
result = pipeline_app.invoke(initial_state, config)

print("\n" + "="*60)
print("POLISHED VISION:")
print("="*60)
print(result.get("polished_vision", ""))
print("="*60)
print("\n⏸️  Pipeline paused for your review.")
print("Run one of these next:")
print("   python resume.py approve")
print("   python resume.py refine \"Your feedback here\"")
