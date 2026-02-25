import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path (mirrors cli.py — needed when resume.py is
# invoked from a directory other than the repo root via an alias or script).
_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from langgraph.types import Command  # noqa: E402

from pipeline import pipeline_app  # noqa: E402

USAGE = """Usage:
  python resume.py approve [<thread-id>]
  python resume.py refine "<your feedback>" [<thread-id>]

If <thread-id> is omitted the last active session is used automatically.
"""


def _thread_id_candidates() -> list[Path]:
    root = Path(__file__).resolve().parent
    # Backward compatibility for sessions written one directory above root.
    return [root / ".thread_id", root.parent / ".thread_id"]


def _load_thread_id(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()

    existing = [p for p in _thread_id_candidates() if p.exists() and p.read_text().strip()]
    if existing:
        newest = max(existing, key=lambda p: p.stat().st_mtime)
        return newest.read_text().strip()

    print("❌ No active session found and no thread-id provided.")
    print("   Run 'gemforge new' or 'python main.py' first, then come back here.")
    print()
    print(USAGE)
    sys.exit(1)


def _print_final_report(result: dict):
    repo_path = result.get("repo_path", "")
    live_url = result.get("live_url")
    print("\n" + "═" * 80)
    print("  🎉  GEMFORGE MISSION COMPLETE")
    print("═" * 80)
    print(f"  Project:  {repo_path or 'N/A'}")
    print(f"  Live URL: {live_url or 'Native project — open in Xcode/Android Studio'}")
    print()
    print("  What to do next:")
    if repo_path:
        print(f"     cd {repo_path}")
    if live_url:
        print(f"     open {live_url}")
    elif repo_path and os.path.isdir(repo_path):
        xcodeprojs = [f for f in os.listdir(repo_path) if f.endswith(".xcodeproj")]
        if xcodeprojs:
            print(f"     open {xcodeprojs[0]}")
        else:
            print("     npm run dev  # or open in Xcode / Android Studio")
    print()
    print("  Progress log:")
    for line in result.get("progress_log", []):
        print(f"    {line}")
    print()
    print("  ✅ Your app is ready. Go ship it.")
    print("═" * 80)


def _finalize_and_report(result: dict):
    """Persist cost and print the final report — shared by approve and any future commands."""
    from tools.cost_tracker import cost_tracker
    cost_tracker.finalize_session()
    cumulative = cost_tracker.get_cumulative_cost()
    print(f"\n   💰 Session: ${cost_tracker.total_cost:.4f} | Tokens: {cost_tracker.total_tokens:,} | Calls: {cost_tracker.calls}")
    print(f"   📊 All-time total: ${cumulative:.4f}")

    if result.get("approval_status") == "pending":
        print("\n⏸️  Pipeline paused for another review gate.")
        print("   python resume.py approve")
        print("   python resume.py refine \"Your feedback\"")
    else:
        _print_final_report(result)


if len(sys.argv) < 2:
    print(USAGE)
    sys.exit(1)

command = sys.argv[1]

if command == "approve":
    thread_id = _load_thread_id(sys.argv[2] if len(sys.argv) > 2 else None)
    config = {"configurable": {"thread_id": thread_id}}
    print(f"   Resuming thread: {thread_id}")
    print("✅ Approved — continuing pipeline...")
    result = pipeline_app.invoke(Command(resume={"action": "approved"}), config)
    _finalize_and_report(result)

elif command == "refine":
    if len(sys.argv) < 3:
        print("❌ Missing feedback text.")
        print(USAGE)
        sys.exit(1)
    feedback = sys.argv[2]
    thread_id = _load_thread_id(sys.argv[3] if len(sys.argv) > 3 else None)
    config = {"configurable": {"thread_id": thread_id}}
    print(f"   Resuming thread: {thread_id}")
    print(f"🔄 Refining with feedback: {feedback}")
    result = pipeline_app.invoke(Command(resume={"action": "rejected", "feedback": feedback}), config)
    print("\n" + "=" * 60)
    print("REFINED VISION:")
    print("=" * 60)
    print(result.get("polished_vision", ""))
    print("=" * 60)
    print("\n⏸️  Review the refined vision, then:")
    print("   python resume.py approve")
    print("   python resume.py refine \"More feedback\"")

else:
    print(f"❌ Unknown command: {command!r}")
    print(USAGE)
    sys.exit(1)
