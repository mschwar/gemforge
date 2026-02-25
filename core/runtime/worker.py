import os
import time
from typing import Callable, Dict, Any
from core.runtime.schema import StepEvent
from core.runtime.event_bus import event_bus
from tools.cost_tracker import cost_tracker

class Worker:
    def __init__(self, step_registry: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]):
        """
        step_registry: Mapping of step_id to the function that executes it.
        The function must take the current pipeline state (dict) and return a dict of state patches.
        """
        self.step_registry = step_registry

    def run_once(self, event: StepEvent) -> Dict[str, Any]:
        """Executes a single step.requested event and returns a StepResult patch."""
        step_id = event.step_id
        handler = self.step_registry.get(step_id)
        
        if not handler:
            return {"status": "failed", "error": f"No handler registered for step_id: {step_id}"}
            
        try:
            # The event payload contains the state dict
            state_slice = event.payload.get("state_slice", {})
            
            start_time = time.time()
            start_tokens = cost_tracker.total_tokens
            start_cost = cost_tracker.total_cost

            # Execute the synchronous handler logic
            result = handler(state_slice)
            
            duration = time.time() - start_time
            tokens_used = cost_tracker.total_tokens - start_tokens
            cost_incurred = cost_tracker.total_cost - start_cost

            return {
                "status": "succeeded",
                "state_patch": result,
                "metrics": {
                    "duration_sec": round(duration, 3),
                    "tokens_used": tokens_used,
                    "cost_usd": round(cost_incurred, 6)
                },
                "artifacts": [] # Future: Extract written files
            }
        except Exception as exc:
            return {"status": "retryable_failed", "error": str(exc)}

    def handle_request(self, event_dict: Dict[str, Any]):
        """Callback for incoming step.requested events."""
        event = StepEvent(**event_dict)
        if event.event_type != "step.requested":
            return
            
        print(f"   [WORKER] 🛠️  Processing {event.step_id} for run {event.run_id}...")
        result = self.run_once(event)
        
        # Determine success vs failure event type
        completion_type = "step.completed" if result["status"] == "succeeded" else "step.failed"
        
        # Publish the completion event
        event_bus.publish(StepEvent(
            run_id=event.run_id,
            step_id=event.step_id,
            event_type=completion_type,
            payload=result,
            attempt=event.attempt
        ))
        print(f"   [WORKER] ✅ Finished {event.step_id} ({result['status']})")
