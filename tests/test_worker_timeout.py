import os
import time
import pytest
from unittest.mock import MagicMock, patch
from core.runtime.worker.dispatcher import OrchestratorDispatcher
from core.runtime.schema import StepEvent
from langgraph.types import Command

@pytest.fixture
def mock_app():
    return MagicMock()

def test_dispatcher_tracks_and_times_out(mock_app):
    """Verify that dispatcher identifies and handles a timed-out request."""
    # Set short timeout for test
    with patch.dict(os.environ, {"GEMFORGE_WORKER_TIMEOUT": "1"}):
        dispatcher = OrchestratorDispatcher(mock_app)
        
        event = StepEvent(
            run_id="test-timeout-run",
            step_id="qa",
            event_type="step.requested"
        )
        
        # Track the request
        dispatcher._track_request(event)
        assert "test-timeout-run" in dispatcher._active_requests
        
        # Wait for timeout
        time.sleep(1.5)
        
        # Trigger the monitor check manually instead of waiting for thread
        dispatcher._monitor_loop = MagicMock() # Stop the actual loop if it was running
        
        # Run one check
        dispatcher._handle_timeout("test-timeout-run", "qa")
        
        # Verify app was resumed with failure
        args, _ = mock_app.invoke.call_args
        command = args[0]
        assert command.resume["status"] == "failed"
        assert "Worker timeout" in command.resume["error"]

def test_logged_node_handles_worker_failure():
    """Verify that logged_node decorator processes a failed worker response."""
    from pipeline import logged_node
    
    @logged_node
    def mock_node(state):
        return {"done": True}

    # Simulate a "failed" resume decision from LangGraph
    state = {"run_id": "test-fail", "pipeline_status": "in_progress"}
    
    # Mock interrupt to return a failure status
    with patch("core.runtime.nodes.interrupt", return_value={"status": "failed", "error": "Crash"}):
        with patch.dict(os.environ, {
            "GEMFORGE_WORKER_ENABLED": "true", 
            "GEMFORGE_WORKER_ENABLED_STEPS": "mock",
            "GEMFORGE_IS_WORKER": "false"
        }):
            final_state = mock_node(state)
            
            assert final_state["pipeline_status"] == "blocked"
            assert final_state["error_code"] == "WORKER_FAILURE"
            assert final_state["error_stage"] == "mock"
