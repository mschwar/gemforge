import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pipeline
from tools.ingestor_tools import bundle_context


class ContextBundlingTests(unittest.TestCase):
    def test_bundle_context_enforces_budgets_and_emits_stats(self):
        root = Path(tempfile.mkdtemp(prefix="gemforge-context-budget-"))
        for idx in range(5):
            (root / f"doc-{idx}.md").write_text("x" * 120, encoding="utf-8")

        bundle, stats = bundle_context(
            str(root),
            raw_idea="general app",
            max_file_size=60,
            max_files=2,
            max_total_chars=140,
            max_total_bytes=180,
            include_stats=True,
        )

        self.assertIn("<directory_context", bundle)
        self.assertLessEqual(stats["included_files"], 2)
        self.assertGreater(stats["dropped_by_budget"], 0)
        self.assertGreaterEqual(stats["truncated_files"], 1)
        self.assertEqual(len(stats["included_paths"]), stats["included_files"])
        self.assertGreater(stats["estimated_tokens"], 0)

    def test_bundle_context_prioritizes_idea_relevant_files(self):
        root = Path(tempfile.mkdtemp(prefix="gemforge-context-priority-"))
        (root / "general-notes.md").write_text("General notes", encoding="utf-8")
        (root / "billing-rules.md").write_text("Billing business rules", encoding="utf-8")
        (root / "architecture.md").write_text("Architecture details", encoding="utf-8")

        _bundle, stats = bundle_context(
            str(root),
            raw_idea="billing reconciliation tool",
            max_files=1,
            max_total_chars=5000,
            max_total_bytes=5000,
            include_stats=True,
        )

        self.assertEqual(stats["included_files"], 1)
        self.assertEqual(stats["included_paths"][0], "billing-rules.md")


class GeneratorGuardTests(unittest.TestCase):
    @patch("pipeline.parse_platform_manifest", return_value={"template": "nextjs", "selected_platform": "nextjs"})
    @patch(
        "pipeline.apply_template",
        return_value={
            "metadata": {"supports_llm_generators": True},
            "platform": "nextjs",
            "name": "nextjs",
            "context": {},
            "validation": {"valid": True},
        },
    )
    @patch("pipeline.load_prompt", return_value="generator-prompt")
    @patch("pipeline.cost_aware_invoke", return_value=SimpleNamespace(content="No generated blocks here"))
    @patch("tools.executor_tools.parse_and_save_generated_code", return_value=[])
    @patch.dict("os.environ", {"GEMFORGE_MIN_GENERATOR_WRITES": "1"}, clear=False)
    def test_code_orchestrator_fails_on_zero_generated_writes(
        self,
        _mock_codegen_parser,
        _mock_llm,
        _mock_prompt_loader,
        _mock_apply_template,
        _mock_manifest_parser,
    ):
        repo = Path(tempfile.mkdtemp(prefix="gemforge-orchestrator-"))
        state = {
            "run_id": "gem-phase3-test",
            "raw_idea": "generator guard",
            "repo_path": str(repo),
            "polished_vision": "vision",
            "audited_context": "audit",
            "selected_template": "nextjs",
        }

        orchestrator = getattr(pipeline.code_orchestrator_node, "__wrapped__", pipeline.code_orchestrator_node)
        with self.assertRaises(ValueError) as raised:
            orchestrator(state)

        self.assertIn("GENERATOR_OUTPUT_MALFORMED", str(raised.exception))

        failure_path = repo / "GENERATOR_FAILURE.json"
        self.assertTrue(failure_path.exists())
        payload = json.loads(failure_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["error_code"], "GENERATOR_OUTPUT_MALFORMED")
        self.assertEqual(payload["generator_write_counts"]["ui_code_generator"], 0)
        self.assertEqual(len(payload["malformed_generators"]), 3)


if __name__ == "__main__":
    unittest.main()
