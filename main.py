from dotenv import load_dotenv
load_dotenv()

import sys
from pipeline import get_pipeline_app
from state import create_initial_pipeline_state


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py \"Your raw idea\"")
        sys.exit(1)

    raw_idea = sys.argv[1]
    thread_id = "gem-" + raw_idea[:40].replace(" ", "-").replace("/", "")
    config = {"configurable": {"thread_id": thread_id}}

    # Save thread_id so resume.py can find this session automatically
    with open(".thread_id", "w") as f:
        f.write(thread_id)

    # Use disciplined factory (never manual dict again)
    initial_state = create_initial_pipeline_state(raw_idea)

    print(f"🚀 Starting GemForge (Discipline v1.0 ENFORCED)")
    print(f"   Thread ID: {thread_id}")
    print(f"   Idea: {raw_idea[:80]}")

    result = get_pipeline_app().invoke(initial_state, config)

    print("\n" + "="*60)
    print("POLISHED VISION:")
    print("="*60)
    print(result.get("polished_vision", ""))
    print("="*60)
    print("\n⏸️   Pipeline paused for your review.")
    print("Run one of these next:")
    print("   python resume.py approve")
    print("   python resume.py refine \"Your feedback here\"")

if __name__ == "__main__":
    main()
