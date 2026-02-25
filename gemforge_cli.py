#!/usr/bin/env python
from dotenv import load_dotenv
load_dotenv()

import sys
from pipeline import pipeline_app
from state import PipelineState
import os


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "new":
        print("Usage:   python gemforge_cli.py new \"Your raw idea here\"")
        print("Example: python gemforge_cli.py new \"A habit tracker that feels like a Tamagotchi\"")
        sys.exit(1)

    raw_idea = sys.argv[2]
    thread_id = f"gem-{raw_idea[:60].replace(' ', '-').replace('/', '')}"

    # Save thread_id so resume.py can find it
    with open(".thread_id", "w") as f:
        f.write(thread_id)

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    GEMFORGE v1.0 — LIVE                      ║
║                Raw Idea → Live App in <10 min                ║
╚══════════════════════════════════════════════════════════════╝

  Idea:   {raw_idea[:60]}
  Thread: {thread_id}
    """)

    initial_state: PipelineState = {
        "raw_idea": raw_idea,
        "polished_vision": "",
        "vision_approved": False,
        "human_feedback": None,
        "canonical_docs": {},
        "repo_path": "",
        "repo_created": False,
        "current_phase": "vision",
        "progress_log": [],
        "approval_status": "pending",
        "architecture_complete": False,
        "frontend_complete": False,
        "backend_complete": False,
        "data_complete": False,
        "qa_complete": False,
        "infra_complete": False,
        "cicd_complete": False,
        "sre_complete": False,
        "deploy_complete": False,
        "live_url": None,
        "deploy_status": None,
    }

    config = {"configurable": {"thread_id": thread_id}}

    print("🚀 Starting full 13-agent factory...\n")
    result = pipeline_app.invoke(initial_state, config)

    polished = result.get("polished_vision", "")
    if polished:
        print("\n" + "="*70)
        print("POLISHED VISION")
        print("="*70)
        print(polished)

    print("\n" + "="*70)
    print("⏸️  APPROVAL GATE — review the vision above, then run:")
    print()
    print("   python resume.py approve")
    print("   python resume.py refine \"Your feedback here\"")
    print("="*70)


def print_final_report(result: dict):
    print("\n" + "="*70)
    print("🎉  GEMFORGE MISSION COMPLETE")
    print("="*70)
    print(f"  Project:  {result.get('repo_path', 'N/A')}")
    print(f"  Live URL: {result.get('live_url', 'Deployment skipped')}")
    print(f"  Status:   {result.get('deploy_status', 'N/A')}")
    print("\n  Progress log:")
    for line in result.get("progress_log", []):
        print(f"    {line}")
    print("\n  ✅ Your app is live. Go ship it.")
    print("="*70)


if __name__ == "__main__":
    main()
