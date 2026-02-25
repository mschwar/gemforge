import json
import time
import sys
import os
from pathlib import Path

# Set worker mode before importing pipeline to ensure decorators see it
os.environ["GEMFORGE_IS_WORKER"] = "true"

# Add repo root to sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pipeline
from core.runtime.outbox_store import outbox_store
from core.runtime.worker import Worker

# Dynamically discover all nodes
REGISTRY = {
    name.replace("_node", ""): func 
    for name, func in pipeline.__dict__.items() 
    if name.endswith("_node") and callable(func)
}

def main():
    """Background worker process to poll event_outbox for step.requested events."""
    worker = Worker(step_registry=REGISTRY)
    
    print("🚀 Runtime Worker starting...")
    print(f"   Registered steps: {len(REGISTRY)} nodes discovered")
    print("   Monitoring event_outbox for step.requested events...")

    try:
        while True:
            # 1. Fetch ONLY step.requested events
            rows = outbox_store.get_unpublished_events(limit=10, event_type_prefix="step.requested")
            
            if not rows:
                time.sleep(1) # Chill if nothing to do
                continue

            # 2. Process each event
            processed_ids = []
            for row in rows:
                event_data = json.loads(row["event_json"])
                
                # Execute the worker logic (this also publishes the step.completed event to the bus)
                worker.handle_request(event_data)
                
                processed_ids.append(row["id"])

            # 3. Mark the requests as published so they aren't processed again
            outbox_store.mark_as_published(processed_ids)
            
    except KeyboardInterrupt:
        print("\\n👋 Worker shutting down.")

if __name__ == "__main__":
    main()
