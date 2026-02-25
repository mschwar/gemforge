import pytest
from unittest.mock import MagicMock, patch
from core.repair.agentic_loop import repair_node
from core.build.hasher import calculate_string_hash

def test_repair_node_dynamic_strategy_on_identical_patch():
    """Verify that repair_node changes strategy when an identical patch is proposed."""
    state = {
        "run_id": "test-repair-diversity",
        "repo_path": "/tmp/mock-project",
        "selected_platform": "web",
        "test_report": "Jest FAILED",
        "repair_count": 0,
        "repair_history": []
    }
    
    identical_patch = "===file.js===\nconsole.log('fixed');"
    new_patch = "===file.js===\nconsole.log('REALLY fixed');"
    
    with patch("core.repair.agentic_loop.load_prompt", return_value="surgeon prompt"), \
         patch("core.repair.agentic_loop.cost_aware_invoke") as mock_invoke, \
         patch("core.repair.agentic_loop.run_tests", return_value={"success": False, "report": "Jest FAILED"}), \
         patch("core.repair.agentic_loop.ProjectSandbox"), \
         patch("core.repair.agentic_loop.parse_and_save_generated_code", return_value=[]):
        
        # 1st repair attempt
        mock_invoke.return_value = MagicMock(content=identical_patch)
        result1 = repair_node(state)
        state.update(result1)
        
        # 2nd repair attempt: first return identical, then return new
        mock_invoke.reset_mock()
        mock_invoke.side_effect = [
            MagicMock(content=identical_patch), # triggers diversification
            MagicMock(content=new_patch)
        ]
        
        result2 = repair_node(state)
        
        # Verify diversification triggered
        assert mock_invoke.call_count == 2
        
        # Verify diversification message
        args, _ = mock_invoke.call_args
        messages = args[0]
        assert any("EMERGENCY DIVERSIFICATION REQUIRED" in m.content for m in messages if hasattr(m, "content"))
        
        assert result2["repair_status"] == "failed"
        assert len(result2["repair_history"]) == 2
        assert result2["repair_history"][-1]["patch_hash"] != result2["repair_history"][0]["patch_hash"]

def test_repair_node_stalls_after_diversity_exhausted():
    """Verify that repair_node eventually stalls if diversification also fails."""
    state = {
        "run_id": "test-repair-exhausted",
        "repo_path": "/tmp/mock-project",
        "selected_platform": "web",
        "test_report": "Jest FAILED",
        "repair_count": 1,
        "repair_history": [{"patch_hash": "somehash"}]
    }
    
    identical_patch = "===file.js===\nconsole.log('fixed');"
    state["repair_history"][0]["patch_hash"] = calculate_string_hash(identical_patch)
    
    with patch("core.repair.agentic_loop.load_prompt", return_value="surgeon prompt"), \
         patch("core.repair.agentic_loop.cost_aware_invoke", return_value=MagicMock(content=identical_patch)) as mock_invoke, \
         patch("core.repair.agentic_loop.run_tests", return_value={"success": False, "report": "Jest FAILED"}), \
         patch("core.repair.agentic_loop.ProjectSandbox"), \
         patch("core.repair.agentic_loop.parse_and_save_generated_code", return_value=[]):
        
        result = repair_node(state)
        
        # Should try 3 times (initial + 2 retries)
        assert mock_invoke.call_count == 3
        assert result["repair_status"] == "stalled_diversity_exhausted"
