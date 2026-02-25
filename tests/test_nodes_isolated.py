import pytest
from unittest.mock import MagicMock, patch
from core.pipeline_stages.nodes.vision_polisher import vision_polisher_node
from core.pipeline_stages.nodes.document_auditor import document_auditor_node

def test_vision_polisher_node_isolated():
    state = {
        "raw_idea": "test idea",
        "polished_vision": "",
        "audited_context": None,
        "human_feedback": None
    }
    
    with patch("core.pipeline_stages.nodes.vision_polisher.load_prompt", return_value="prompt"), \
         patch("core.pipeline_stages.nodes.vision_polisher.cost_aware_invoke", return_value=MagicMock(content="polished content")):
        
        result = vision_polisher_node(state)
        assert result["polished_vision"] == "polished content"
        assert result["approval_status"] == "pending"

def test_document_auditor_node_isolated():
    state = {
        "raw_idea": "test idea",
        "source_docs_path": "/tmp/mock-docs"
    }
    
    mock_stats = {
        "included_files": 1,
        "total_chars": 100,
        "estimated_tokens": 20,
        "dropped_by_budget": 0,
        "dropped_oversized_file": 0,
        "truncated_files": 0
    }
    
    with patch("core.pipeline_stages.nodes.document_auditor.bundle_context", return_value=("bundle", mock_stats)), \
         patch("core.pipeline_stages.nodes.document_auditor.load_prompt", return_value="prompt"), \
         patch("core.pipeline_stages.nodes.document_auditor.cost_aware_invoke", return_value=MagicMock(content="audited content")), \
         patch("os.path.exists", return_value=True):
        
        result = document_auditor_node(state)
        assert result["audited_context"] == "audited content"
        assert "✅ Document Audit complete" in result["progress_log"][0]
