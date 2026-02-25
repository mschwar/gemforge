import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID
from unittest.mock import patch

from src.gemforge import cli as cli_module
from tools import file_tools


class Phase2IdentityStateTests(unittest.TestCase):
    @patch("tools.file_tools.run_command", return_value=SimpleNamespace(returncode=0, stdout="", stderr=""))
    @patch("tools.file_tools._timestamp_for_project", return_value="20260225-120000")
    def test_create_project_structure_avoids_collisions(self, _mock_timestamp, _mock_run_command):
        projects_root = Path(tempfile.mkdtemp(prefix="gemforge-projects-"))

        # Pre-create the first candidate to force the collision branch.
        (projects_root / "my-gem-20260225-120000").mkdir(parents=True, exist_ok=True)

        with patch.object(file_tools, "PROJECTS_ROOT", projects_root):
            repo_path = file_tools.create_project_structure("My Gem")

        self.assertEqual(Path(repo_path).name, "my-gem-20260225-120000-1")
        self.assertTrue((Path(repo_path) / "MASTERBRIEF.md").exists())

    @patch("src.gemforge.cli.uuid4", side_effect=[UUID(int=1), UUID(int=2)])
    @patch("src.gemforge.cli.time.time_ns", side_effect=[1, 2])
    def test_build_thread_id_is_collision_resistant(self, _mock_time_ns, _mock_uuid4):
        thread_one = cli_module._build_thread_id("An ear training app")
        thread_two = cli_module._build_thread_id("An ear training app")

        self.assertTrue(thread_one.startswith("gem-An-ear-training-app-"))
        self.assertTrue(thread_two.startswith("gem-An-ear-training-app-"))
        self.assertNotEqual(thread_one, thread_two)

    @patch("src.gemforge.cli._finalize_and_report")
    @patch("src.gemforge.cli.get_pipeline_app")
    @patch("src.gemforge.cli._load_thread_id", return_value="gem-demo-thread")
    @patch("src.gemforge.cli.signal.signal")
    def test_resume_refine_finalizes_session_reporting(
        self,
        _mock_signal,
        _mock_load_thread_id,
        mock_get_pipeline_app,
        mock_finalize_and_report,
    ):
        mock_get_pipeline_app.return_value = SimpleNamespace(
            invoke=lambda *_args, **_kwargs: {
                "approval_status": "pending",
                "polished_vision": "Refined vision",
                "progress_log": [],
            }
        )
        args = SimpleNamespace(action="refine", feedback="Tighten scope", thread=None)

        cli_module.cmd_resume(args)

        mock_finalize_and_report.assert_called_once()


if __name__ == "__main__":
    unittest.main()
