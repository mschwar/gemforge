"""Backward-compatible launcher for the human review gate.

Prefer the installed command instead:
  gemforge resume approve
  gemforge resume refine "Your feedback"

This shim translates the legacy `python resume.py approve [<thread-id>]`
interface into the canonical CLI so existing muscle memory keeps working.
"""
import sys
from pathlib import Path

# Ensure repo root is on sys.path (same as cli.py).
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

USAGE = """Usage:
  python resume.py approve [<thread-id>]
  python resume.py refine "<your feedback>" [<thread-id>]

Preferred (after pip install -e .):
  gemforge resume approve [--thread <thread-id>]
  gemforge resume refine "<feedback>" [--thread <thread-id>]
"""

if len(sys.argv) < 2:
    print(USAGE)
    sys.exit(1)

command = sys.argv[1]

# Build a fake args namespace and delegate to cli internals.
from src.gemforge.cli import cmd_resume, _load_thread_id  # noqa: E402


class _Args:
    pass


if command == "approve":
    args = _Args()
    args.action = "approve"
    args.thread = sys.argv[2] if len(sys.argv) > 2 else None
    cmd_resume(args)

elif command == "refine":
    if len(sys.argv) < 3:
        print("❌ Missing feedback text.")
        print(USAGE)
        sys.exit(1)
    args = _Args()
    args.action = "refine"
    args.feedback = sys.argv[2]
    args.thread = sys.argv[3] if len(sys.argv) > 3 else None
    cmd_resume(args)

else:
    print(f"❌ Unknown command: {command!r}")
    print(USAGE)
    sys.exit(1)
