import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pipeline
from src.gemforge import cli as cli_module


class Phase5FlowCoverageTests(unittest.TestCase):
    def test_new_pauses_then_resume_approve_continues_pipeline(self):
        thread_id = "gem-phase5-thread"
        thread_file = Path(tempfile.mkdtemp(prefix="gemforge-thread-")) / ".thread_id"
        approve_result = {
            "approval_status": "approved",
            "pipeline_status": "success",
            "repo_path": "/tmp/gem",
            "live_url": "https://example.vercel.app",
            "progress_log": [],
        }
        invocations = []

        def _invoke(payload, config):
            invocations.append((payload, config))
            if isinstance(payload, dict):
                return {"approval_status": "pending", "polished_vision": "Draft vision", "progress_log": []}
            return approve_result

        app = SimpleNamespace(invoke=_invoke)
        fake_cost_tracker = SimpleNamespace(
            total_cost=0.0,
            total_tokens=0,
            calls=0,
            finalize_session=lambda: None,
            get_cumulative_cost=lambda: 0.0,
        )

        with (
            patch("src.gemforge.cli.validate_environment"),
            patch("src.gemforge.cli.signal.signal"),
            patch("src.gemforge.cli._build_thread_id", return_value=thread_id),
            patch("src.gemforge.cli._find_thread_id_path", return_value=str(thread_file)),
            patch("src.gemforge.cli._load_thread_id", return_value=thread_id),
            patch("src.gemforge.cli.get_pipeline_app", return_value=app),
            patch("tools.cost_tracker.cost_tracker", fake_cost_tracker),
            patch("src.gemforge.cli._finalize_and_report") as finalize_report,
        ):
            new_output = io.StringIO()
            with redirect_stdout(new_output):
                cli_module.cmd_new(SimpleNamespace(idea="Phase 5 idea", context=None))

            resume_output = io.StringIO()
            with redirect_stdout(resume_output):
                cli_module.cmd_resume(SimpleNamespace(action="approve", thread=None))

        self.assertEqual(thread_file.read_text(encoding="utf-8"), thread_id)
        self.assertIn("Pipeline paused for human review.", new_output.getvalue())
        self.assertIn("Approved — continuing pipeline", resume_output.getvalue())
        self.assertEqual(len(invocations), 2)
        self.assertEqual(invocations[0][1], {"configurable": {"thread_id": thread_id}})
        self.assertEqual(invocations[1][0].resume, {"action": "approved"})
        finalize_report.assert_called_once_with(approve_result)

    def test_resume_refine_keeps_pending_and_prints_refined_vision(self):
        thread_id = "gem-phase5-thread-refine"
        result = {
            "approval_status": "pending",
            "polished_vision": "Refined vision copy",
            "progress_log": [],
        }
        app = SimpleNamespace(invoke=MagicMock(return_value=result))

        with (
            patch("src.gemforge.cli.signal.signal"),
            patch("src.gemforge.cli._load_thread_id", return_value=thread_id),
            patch("src.gemforge.cli.get_pipeline_app", return_value=app),
            patch("src.gemforge.cli._finalize_and_report") as finalize_report,
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                cli_module.cmd_resume(
                    SimpleNamespace(action="refine", feedback="Tighten onboarding scope", thread=None)
                )

        command = app.invoke.call_args.args[0]
        self.assertEqual(command.resume, {"action": "rejected", "feedback": "Tighten onboarding scope"})
        self.assertIn("REFINED VISION", output.getvalue())
        self.assertIn("Refined vision copy", output.getvalue())
        finalize_report.assert_called_once_with(result)


class Phase5GatingInteractionTests(unittest.TestCase):
    @patch("core.pipeline_stages.failure_semantics.is_native_mobile", return_value=False)
    @patch("pipeline.deploy_to_vercel", return_value=None)
    @patch(
        "pipeline.push_to_github",
        return_value={
            "success": True,
            "repo_url": "https://github.com/acme/gemforge-phase5",
            "pr_url": "",
        },
    )
    def test_deploy_failure_then_publish_success_preserves_partial_status(
        self,
        _mock_publish,
        _mock_deploy,
        _mock_native_check,
    ):
        deploy = getattr(pipeline.deploy_node, "__wrapped__", pipeline.deploy_node)
        git_publish = getattr(pipeline.git_publish_node, "__wrapped__", pipeline.git_publish_node)

        deploy_result = deploy(
            {
                "repo_path": "/tmp/gem",
                "selected_platform": "nextjs",
                "pipeline_status": "success",
            }
        )
        self.assertEqual(deploy_result["pipeline_status"], "partial")
        self.assertEqual(deploy_result["error_code"], "DEPLOY_FAILED")

        publish_result = git_publish(
            {
                "repo_path": "/tmp/gem",
                "raw_idea": "phase 5 flow",
                "pipeline_status": deploy_result["pipeline_status"],
            }
        )
        self.assertTrue(publish_result["git_published"])
        self.assertEqual(publish_result["pipeline_status"], "partial")
        self.assertEqual(pipeline.route_after_git_publish(publish_result), "shipping")

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
    def test_publish_failure_blocks_pipeline_and_routes_to_end(self, _mock_publish):
        git_publish = getattr(pipeline.git_publish_node, "__wrapped__", pipeline.git_publish_node)
        result = git_publish({"repo_path": "/tmp/gem", "raw_idea": "phase 5 flow"})

        self.assertFalse(result["git_published"])
        self.assertEqual(result["pipeline_status"], "blocked")
        self.assertEqual(result["error_code"], "GIT_PUBLISH_FAILED")
        self.assertEqual(pipeline.route_after_git_publish(result), "end")


if __name__ == "__main__":
    unittest.main()
