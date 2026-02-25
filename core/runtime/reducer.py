from typing import Dict, Any, List
from core.runtime.schema import StepEvent

class StateReducer:
    """Rehydrates pipeline state from the event log."""
    
    def reduce(self, events: List[Dict[str, Any]], initial_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fold a sequence of events into a final state dict."""
        state = initial_state.copy() if initial_state else {}
        
        for event_dict in events:
            event = StepEvent(**event_dict)
            
            if event.event_type == "step.completed":
                patch = event.payload.get("state_patch", {})
                metrics = event.payload.get("metrics", {})
                
                # Apply metrics
                if metrics:
                    state["total_tokens"] = state.get("total_tokens", 0) + metrics.get("tokens_used", 0)
                    state["total_cost"] = state.get("total_cost", 0.0) + metrics.get("cost_usd", 0.0)

                # Apply state patch
                for k, v in patch.items():
                    if k == "progress_log" and isinstance(v, list):
                        state.setdefault("progress_log", []).extend(v)
                    else:
                        state[k] = v
                        
        return state

state_reducer = StateReducer()
