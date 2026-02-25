import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import pipeline
from src.gemforge import cli as cli_module
from tools.file_tools import CommandFailure, run_command


class Phase4FailureSemanticsTests(unittest.TestCase):
    @patch("tools.file_tools.subprocess.run")
    def test_critical_command_failure_raises_with_payload(self, mock_run):
        mock_run.return_value = SimpleNamespace(returncode=1, stderr="fatal: auth missing", stdout="")

        with self.assertRaises(CommandFailure) as raised:
            run_command(
                ["git", "commit", "-m", "test"],
                cwd="/tmp",
                critical=True,
                error_code="GIT_BOOTSTRAP_COMMIT_FAILED",
                error_stage="bootstrapper",
                operator_action="Configure git user.name/user.email and rerun.",
            )

        payload = raised.exception.payload
        self.assertEqual(payload["error_code"], "GIT_BOOTSTRAP_COMMIT_FAILED")
        self.assertEqual(payload["error_stage"], "bootstrapper")
        self.assertIn("Configure git user.name", payload["operator_action"])

    @patch(
        "pipeline.push_to_github",
        return_value={
            "success": False,
            "repo_url": "",
            "pr_url": "",
            "error": "gh auth token missing",
            "error_code": "GIT_PUBLISH_FAILED",
            "error_stage": "git_publish",
            "operator_action": "Authenticate GitHub CLI and rerun publish.",
        },
    )
    def test_git_publish_failure_returns_blocked_error_envelope(self, _mock_push):
        node = getattr(pipeline.git_publish_node, "__wrapped__", pipeline.git_publish_node)
        result = node({"repo_path": "/tmp/example", "raw_idea": "idea"})

        self.assertFalse(result["git_published"])
        self.assertEqual(result["pipeline_status"], "blocked")
        self.assertEqual(result["error_code"], "GIT_PUBLISH_FAILED")
        self.assertEqual(result["error_stage"], "git_publish")
        self.assertIn("Authenticate GitHub CLI", result["operator_action"])

    def test_git_publish_route_stops_on_failure(self):
        self.assertEqual(pipeline.route_after_git_publish({"git_published": False}), "end")
        self.assertEqual(pipeline.route_after_git_publish({"git_published": True}), "shipping")

    def test_cli_report_renders_blocked_and_partial_statuses(self):
        blocked = {
            "repo_path": "/tmp/example",
            "live_url": None,
            "pipeline_status": "blocked",
            "error_code": "GIT_PUBLISH_FAILED",
            "error_stage": "git_publish",
            "operator_action": "Authenticate GitHub CLI and rerun publish.",
            "progress_log": ["❌ Git publish blocked"],
        }
        partial = {
            "repo_path": "/tmp/example",
            "live_url": None,
            "pipeline_status": "partial",
            "error_code": "DEPLOY_FAILED",
            "error_stage": "deploy",
            "operator_action": "Run `npx vercel --prod --yes` from the generated project directory.",
            "progress_log": ["⚠️ Deploy failed"],
        }

        blocked_buffer = io.StringIO()
        with redirect_stdout(blocked_buffer):
            cli_module._print_final_report(blocked)
        blocked_output = blocked_buffer.getvalue()
        self.assertIn("MISSION BLOCKED", blocked_output)
        self.assertIn("GIT_PUBLISH_FAILED", blocked_output)
        self.assertIn("Authenticate GitHub CLI", blocked_output)

        partial_buffer = io.StringIO()
        with redirect_stdout(partial_buffer):
            cli_module._print_final_report(partial)
        partial_output = partial_buffer.getvalue()
        self.assertIn("MISSION PARTIAL", partial_output)
        self.assertIn("DEPLOY_FAILED", partial_output)


if __name__ == "__main__":
    unittest.main()
