from dotenv import load_dotenv
load_dotenv()
from pipeline import pipeline_app
from langgraph.types import Command
import sys

if len(sys.argv) < 2:
    print("Usage: python resume.py approve")
    print("       python resume.py refine \"your feedback\"")
    sys.exit(1)

# Read thread_id saved by main.py
try:
    with open(".thread_id", "r") as f:
        thread_id = f.read().strip()
except FileNotFoundError:
    print("❌ No active session found. Run main.py first.")
    sys.exit(1)

config = {"configurable": {"thread_id": thread_id}}
print(f"   Resuming thread: {thread_id}")

if sys.argv[1] == "approve":
    print("✅ Approved — continuing to Ruthless Interrogator...")
    result = pipeline_app.invoke(Command(resume={"action": "approved"}), config)
    print("\n🎉 Interrogation complete! Review the questions above.")

elif sys.argv[1] == "refine":
    if len(sys.argv) < 3:
        print("Usage: python resume.py refine \"your feedback\"")
        sys.exit(1)
    feedback = sys.argv[2]
    print(f"🔄 Refining with feedback: {feedback}")
    result = pipeline_app.invoke(Command(resume={"action": "rejected", "feedback": feedback}), config)
    print("\n" + "="*60)
    print("REFINED VISION:")
    print("="*60)
    print(result.get("polished_vision", ""))
    print("="*60)
    print("\n⏸️  Review the refined vision, then:")
    print("   python resume.py approve")
    print("   python resume.py refine \"More feedback\"")

else:
    print(f"Unknown command: {sys.argv[1]}")
    print("Use 'approve' or 'refine'")
    sys.exit(1)
