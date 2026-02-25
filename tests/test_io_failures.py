import pytest
from unittest.mock import MagicMock, patch
from pipeline import bootstrapper_node
from core.runtime.sandbox import ProjectSandbox

def test_bootstrapper_handles_permission_error():
    """Verify that bootstrapper marks state as blocked on PermissionError."""
    state = {
        "run_id": "test-io-fail",
        "raw_idea": "test idea",
        "pipeline_status": "in_progress",
        "audited_context": "audit context",
        "canonical_docs": {"_raw_output": "raw output"},
        "progress_log": []
    }
    
    # Mock create_project_structure to return a path
    with patch("core.pipeline_stages.nodes.bootstrapper.create_project_structure", return_value="/tmp/mock-project"), \
         patch("core.pipeline_stages.nodes.bootstrapper.ProjectSandbox.safe_write", side_effect=PermissionError("Mock Permission Denied")):
        
        from pipeline import bootstrapper_node
        
        # Disable worker proxy and cache for this test
        with patch.dict("os.environ", {"GEMFORGE_WORKER_ENABLED": "false", "GEMFORGE_USE_CACHE": "false"}):
             result = bootstrapper_node(state)
             
             assert result["pipeline_status"] == "blocked"
             assert result["error_code"] == "IO_PERMISSION_FAILURE"
             assert "Mock Permission Denied" in result["operator_action"]

def test_architecture_handles_permission_error():
    """Verify architecture_node marks state as blocked on PermissionError."""
    state = {
        "run_id": "test-arch-fail",
        "repo_path": "/tmp/mock-project",
        "polished_vision": "vision",
        "audited_context": "audit",
        "canonical_docs": {},
        "progress_log": []
    }
    
    with patch("core.pipeline_stages.nodes.architecture.load_prompt", return_value="prompt"), \
         patch("core.pipeline_stages.nodes.architecture.cost_aware_invoke", return_value=MagicMock(content="arch content")), \
         patch("core.pipeline_stages.nodes.architecture.ProjectSandbox.safe_write", side_effect=PermissionError("Mock Permission Denied")):
        
        from pipeline import architecture_node
        with patch.dict("os.environ", {"GEMFORGE_WORKER_ENABLED": "false", "GEMFORGE_USE_CACHE": "false"}):
            result = architecture_node(state)
            assert result["pipeline_status"] == "blocked"
            assert result["error_code"] == "IO_PERMISSION_FAILURE"
            assert "Mock Permission Denied" in result["operator_action"]
