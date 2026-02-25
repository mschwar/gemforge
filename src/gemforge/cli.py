#!/usr/bin/env python
from dotenv import load_dotenv
load_dotenv()

import sys
import argparse
from pipeline import pipeline_app
from state import create_initial_pipeline_state
from core.discipline.enforcer import enforce_protocol

@enforce_protocol(
    step_number=5,
    short_name="CLIEntry",
    description="Production gemforge CLI (gemforge new \"idea\" --context path)"
)
def main():
    parser = argparse.ArgumentParser(description="GemForge AI Product Factory")
    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser("new", help="Create a new gem")
    new_parser.add_argument("idea", help="The raw idea for your app")
    new_parser.add_argument("--context", help="Path to a directory of existing documents/code", default=None)

    args = parser.parse_args()

    if args.command != "new":
        parser.print_help()
        sys.exit(1)

    raw_idea = args.idea
    source_docs_path = args.context
    
    thread_id = f"gem-{raw_idea[:60].replace(' ', '-').replace('/', '')}"

    with open(".thread_id", "w") as f:
        f.write(thread_id)

    print("\n" + "═"*80)
    print("                  GEMFORGE  —  AI Product Factory v1.0")
    print("                    Raw Idea → Complete Runnable App")
    print("═"*80)
    print(f"  Idea:   {raw_idea[:76]}")
    if source_docs_path:
        print(f"  Docs:   {source_docs_path}")
    print(f"  Thread: {thread_id}")
    print("═"*80)

    initial_state = create_initial_pipeline_state(raw_idea, source_docs_path)
    config = {"configurable": {"thread_id": thread_id}}

    print("\n🚀 Launching full factory...\n")
    result = pipeline_app.invoke(initial_state, config)

    from tools.cost_tracker import cost_tracker
    print(f"   💰 Total cost: ${cost_tracker.total_cost:.4f} | Tokens: {cost_tracker.total_tokens} | Calls: {cost_tracker.calls}")
    print_final_report(result)

def print_final_report(result: dict):
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
