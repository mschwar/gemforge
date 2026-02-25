#!/usr/bin/env python
from dotenv import load_dotenv
load_dotenv()

import sys
from pipeline import pipeline_app
from state import create_initial_pipeline_state
from core.discipline.enforcer import enforce_protocol


@enforce_protocol(
    step_number=5,
    short_name="CLIEntry",
    description="Primary GemForge CLI launch (gemforge_cli.py new \"idea\") — full pipeline with full discipline"
)
def main():
    if len(sys.argv) < 3 or sys.argv[1] != "new":
        print("Usage: python gemforge_cli.py new \"Your raw idea\"")
        sys.exit(1)

    raw_idea = sys.argv[2]
    thread_id = f"gem-{raw_idea[:60].replace(' ', '-').replace('/', '')}"

    # Save thread_id so resume.py can find it
    with open(".thread_id", "w") as f:
        f.write(thread_id)

    print("\n" + "═"*80)
    print("                  GEMFORGE  —  AI Product Factory v1.0")
    print("                    Raw Idea → Complete Runnable App")
    print("═"*80)
    print(f"  Idea:   {raw_idea[:76]}")
    print(f"  Thread: {thread_id}")
    print("═"*80)

    # Use disciplined factory (never manual dict again)
    initial_state = create_initial_pipeline_state(raw_idea)

    config = {"configurable": {"thread_id": thread_id}}

    print("\n🚀 Launching full factory...\n")
    result = pipeline_app.invoke(initial_state, config)

    polished = result.get("polished_vision", "")
    if polished:
        print("\n" + "═"*80)
        print("  POLISHED VISION")
        print("═"*80)
        print(polished)

    print("\n" + "═"*80)
    print("  ⏸️   APPROVAL GATE — review the vision above, then run:")
    print()
    print("     python resume.py approve")
    print("     python resume.py refine \"Your feedback here\"")
    print("═"*80)


def print_final_report(result: dict):
    """Helper — remains untouched (called later by resume/pipeline)"""
    repo_path = result.get("repo_path", "")
    live_url = result.get("live_url")

    print("\n" + "═"*80)
    print("  🎉  GEMFORGE MISSION COMPLETE")
    print("═"*80)
    print(f"  Project:  {repo_path or 'N/A'}")
    print(f"  Live URL: {live_url or 'Native project — open in Xcode'}")
    print()
    print("  What to do next:")
    if repo_path:
        print(f"     cd {repo_path}")
    if live_url:
        print(f"     open {live_url}")
    elif repo_path:
        import os
        xcodeprojs = [f for f in os.listdir(repo_path) if f.endswith(".xcodeproj")] if os.path.isdir(repo_path) else []
        if xcodeprojs:
            print(f"     open {xcodeprojs[0]}")
        else:
            print("     npm run dev  # or open in Xcode")
    print()
    print("  Progress log:")
    for line in result.get("progress_log", []):
        print(f"    {line}")
    print()
    print("  ✅ Your app is ready. Go ship it.")
    print("═"*80)


if __name__ == "__main__":
    main()
