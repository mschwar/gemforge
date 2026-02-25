import logging
from typing import Any

logger = logging.getLogger("gemforge")

def handle_io_error(state: dict[str, Any], error: Exception, stage: str, critical: bool = True, error_code: str = "IO_PERMISSION_FAILURE") -> dict[str, Any]:
    """Standardized handler for I/O errors, marking the pipeline as blocked if critical."""
    logger.error(f"Error in {stage}: {error}", extra={"run_id": state.get("run_id"), "stage": stage})
    
    if critical:
        state["pipeline_status"] = "blocked"
        state["error_code"] = error_code
        state["error_stage"] = stage
        state["operator_action"] = f"Failure during {stage}. Details: {error}"
    else:
        if "progress_log" not in state:
            state["progress_log"] = []
        state["progress_log"].append(f"⚠️ Warning: Failed in {stage}: {error}")
        
    return state
