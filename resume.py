from dotenv import load_dotenv

load_dotenv()
import sys
from pathlib import Path

from langgraph.types import Command

from pipeline import pipeline_app

_THREAD_ID_FILE = Path(__file__).resolve().parent / ".thread_id"

USAGE = """Usage:
  python resume.py approve [<thread-id>]
  python resume.py refine "<your feedback>" [<thread-id>]

If <thread-id> is omitted the last active session is used automatically.
"""

def _load_thread_id(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    if _THREAD_ID_FILE.exists():
        tid = _THREAD_ID_FILE.read_text().strip()
        if tid:
            return tid
    print("❌ No active session found and no thread-id provided.")
    print("   Run 'gemforge new' or 'python main.py' first, then come back here.")
    print()
    print(USAGE)
    sys.exit(1)


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
    print("\n🎉 Vision approved — pipeline continues.")

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
