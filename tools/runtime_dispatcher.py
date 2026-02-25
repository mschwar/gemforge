import json
import time
import sys
from pathlib import Path

# Add repo root to sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.runtime.outbox_store import outbox_store
from pipeline import get_pipeline_app
from langgraph.types import Command

def resume_graph(run_id: str, state_patch: dict, metrics: dict = None):
    print(f"   [DISPATCH] 🔄 Resuming graph for {run_id}...")
    try:
        config = {"configurable": {"thread_id": run_id}}
        # LangGraph requires the Command to include the resume data
        resume_data = {"state_patch": state_patch}
        if metrics:
            resume_data["metrics"] = metrics
        get_pipeline_app().invoke(Command(resume=resume_data), config)
    except Exception as e:
        print(f"   [DISPATCH] ❌ Failed to resume {run_id}: {e}")

def main():
    """Background process to poll event_outbox and dispatch events."""
    print("🚀 Runtime Dispatcher starting...")
    print("   Monitoring event_outbox for new events...")

    try:
        while True:
            # 1. Fetch unpublished events (exclude step.requested, which are for workers)
            rows = outbox_store.get_unpublished_events(limit=50, exclude_prefix="step.requested")
            
            if not rows:
                time.sleep(1) # Chill if nothing to do
                continue

            # 2. Process each event
            processed_ids = []
            for row in rows:
                event_data = json.loads(row["event_json"])
                event_id = event_data.get("event_id", "unknown")
                run_id = event_data.get("run_id", "unknown")
                step_id = event_data.get("step_id", "unknown")
                event_type = event_data.get("event_type", "unknown")
                payload = event_data.get("payload", {})

                print(f"   [DISPATCH] {run_id} | {step_id:<20} | {event_type}")
                
                # Phase 2: Resume graph on worker completion
                if event_type == "step.completed" and "state_patch" in payload:
                    resume_graph(run_id, payload["state_patch"], payload.get("metrics"))
                
                processed_ids.append(row["id"])

            # 3. Mark as published in one batch
            outbox_store.mark_as_published(processed_ids)
            
    except KeyboardInterrupt:
        print("\\n👋 Dispatcher shutting down.")

if __name__ == "__main__":
    main()
