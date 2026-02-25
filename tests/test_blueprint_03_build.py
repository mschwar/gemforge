import unittest
import os
import tempfile
import shutil
from pathlib import Path

from core.build.hasher import calculate_string_hash, calculate_dir_hash
from core.build.graph import get_downstream_nodes
from core.build.cache import BuildCache

class TestBlueprint03Build(unittest.TestCase):
    def test_hashing_determinism(self):
        """Verify hashing is consistent for the same input."""
        h1 = calculate_string_hash("hello world")
        h2 = calculate_string_hash("hello world")
        self.assertEqual(h1, h2)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "file1.txt").write_text("content1")
            (tmp_path / "file2.txt").write_text("content2")
            
            hash1 = calculate_dir_hash(tmp_path)
            hash2 = calculate_dir_hash(tmp_path)
            self.assertEqual(hash1, hash2)

    def test_dependency_resolution(self):
        """Verify graph correctly finds downstream dependents."""
        # architecture -> platform_decision -> code_orchestrator -> frontend
        # (based on our static map in core/build/graph.py)
        downstream = get_downstream_nodes("architecture")
        self.assertIn("platform_decision", downstream)
        self.assertIn("code_orchestrator", downstream)
        self.assertIn("frontend", downstream)
        self.assertIn("qa", downstream)
        
        # document_auditor should be upstream of almost everything
        downstream_all = get_downstream_nodes("document_auditor")
        self.assertIn("vision_polisher", downstream_all)
        self.assertIn("weaver", downstream_all)

    def test_cache_hit_miss(self):
        """Verify the cache store correctly retrieves and stores data."""
        with tempfile.NamedTemporaryFile() as tmp:
            cache = BuildCache(db_path=tmp.name)
            
            input_hash = "abc-123"
            step_id = "test_step"
            output = {"result": "success", "data": [1, 2, 3]}
            
            # Miss
            self.assertIsNone(cache.get(input_hash, step_id))
            
            # Set and Hit
            cache.set(input_hash, step_id, output)
            hit = cache.get(input_hash, step_id)
            self.assertEqual(hit["result"], "success")
            self.assertEqual(hit["data"], [1, 2, 3])

if __name__ == "__main__":
    unittest.main()
