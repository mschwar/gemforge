import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pipeline import director_node
from tools.deploy_tools import deploy_to_vercel
from tools.executor_tools import run_tests


class ReliabilityGuardsTests(unittest.TestCase):
    @patch("tools.deploy_tools.subprocess.run")
    def test_deploy_preserves_framework_project(self, mock_run):
        repo = Path(tempfile.mkdtemp(prefix="gemforge-nextjs-"))
        (repo / "package.json").write_text(
            json.dumps({"dependencies": {"next": "14.2.11"}}),
            encoding="utf-8",
        )
        (repo / "next.config.mjs").write_text("export default {}", encoding="utf-8")

        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="https://demo.vercel.app\n",
            stderr="",
        )

        live_url = deploy_to_vercel(str(repo), "web")

        self.assertEqual(live_url, "https://demo.vercel.app")
        self.assertFalse((repo / "index.html").exists())
        self.assertFalse((repo / "vercel.json").exists())

    @patch("tools.deploy_tools.subprocess.run")
    def test_deploy_static_fallback_still_applies_to_non_framework_projects(self, mock_run):
        repo = Path(tempfile.mkdtemp(prefix="gemforge-static-"))
        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="https://static.vercel.app\n",
            stderr="",
        )

        live_url = deploy_to_vercel(str(repo), "web")

        self.assertEqual(live_url, "https://static.vercel.app")
        self.assertTrue((repo / "index.html").exists())
        self.assertTrue((repo / "vercel.json").exists())

    def test_unknown_platform_tests_fail_closed(self):
        repo = Path(tempfile.mkdtemp(prefix="gemforge-qa-"))

        result = run_tests(str(repo), "python-cli")

        self.assertFalse(result["success"])
        self.assertEqual(result["failures"], 1)
        self.assertIn("No dedicated test runner", result["report"])

    @patch("pipeline.load_prompt", return_value="director prompt")
    @patch("pipeline.cost_aware_invoke", return_value=SimpleNamespace(content="Not approved yet"))
    def test_director_no_longer_force_greens_after_three_rejections(self, _mock_invoke, _mock_prompt):
        state = {
            "polished_vision": "vision",
            "repo_path": "",
            "test_report": "Jest FAILED",
            "tests_passed": True,
            "director_rejection_count": 2,
        }

        result = director_node(state)

        self.assertFalse(result["director_approved"])
        self.assertEqual(result["director_rejection_count"], 3)

    @patch("pipeline.load_prompt", return_value="director prompt")
    @patch("pipeline.cost_aware_invoke", return_value=SimpleNamespace(content="GREEN LIGHT"))
    def test_director_blocks_green_when_tests_failed(self, _mock_invoke, _mock_prompt):
        state = {
            "polished_vision": "vision",
            "repo_path": "",
            "test_report": "No dedicated test runner for python-cli",
            "tests_passed": False,
            "director_rejection_count": 0,
        }

        result = director_node(state)

        self.assertFalse(result["director_approved"])
        self.assertEqual(result["director_rejection_count"], 1)


if __name__ == "__main__":
    unittest.main()
