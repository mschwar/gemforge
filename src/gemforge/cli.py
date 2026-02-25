#!/usr/bin/env python
import sys
from pathlib import Path

# Ensure repo root is on sys.path so pipeline.py, tools/, core/, and state.py
# can be imported regardless of the user's current working directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import argparse  # noqa: E402
import datetime  # noqa: E402
import os  # noqa: E402

from pipeline import get_pipeline_app  # noqa: E402
from state import create_initial_pipeline_state  # noqa: E402


def validate_environment():
    """Pre-flight check: fail fast with a clear message before touching anything."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌  ANTHROPIC_API_KEY is not set.")
        print("    Add it to a .env file in the repo root, or export it:")
        print("    export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)
    from tools.file_tools import PROJECTS_ROOT
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)


def cmd_new(args):
    raw_idea = args.idea
    source_docs_path = args.context

    validate_environment()

    thread_id = f"gem-{raw_idea[:60].replace(' ', '-').replace('/', '')}"

    _thread_id_path = _find_thread_id_path()
    with open(_thread_id_path, "w") as f:
        f.write(thread_id)

    print("\n" + "═" * 80)
    print("                  GEMFORGE  —  AI Product Factory")
    print("                    Raw Idea → Complete Runnable App")
    print("═" * 80)
    print(f"  Idea:   {raw_idea[:76]}")
    if source_docs_path:
        print(f"  Docs:   {source_docs_path}")
    print(f"  Thread: {thread_id}")
    print("═" * 80)

    initial_state = create_initial_pipeline_state(raw_idea, source_docs_path)
    config = {"configurable": {"thread_id": thread_id}}

    print("\n🚀 Launching full factory...\n")
    result = get_pipeline_app().invoke(initial_state, config)

    from tools.cost_tracker import cost_tracker
    cost_tracker.finalize_session()
    cumulative = cost_tracker.get_cumulative_cost()
    print(f"\n   💰 Session: ${cost_tracker.total_cost:.4f} | Tokens: {cost_tracker.total_tokens:,} | Calls: {cost_tracker.calls}")
    print(f"   📊 All-time total: ${cumulative:.4f}")

    if result.get("approval_status") == "pending":
        print("\n⏸️  Pipeline paused for human review.")
        print("   Next commands:")
        print("   python resume.py approve")
        print("   python resume.py refine \"Your feedback\"")
        return

    _print_final_report(result)


def cmd_list(args):
    from core.reporting.empire_stats import EmpireStats
    stats = EmpireStats()
    projects = stats.get_recent_projects(limit=args.limit)

    if not projects:
        print("No gems forged yet. Run:  gemforge new \"your idea\"")
        return

    print(f"\n{'═' * 60}")
    print(f"  💎  GemForge Project Fleet  ({len(projects)} shown)")
    print(f"{'═' * 60}")
    for p in projects:
        created = datetime.datetime.fromtimestamp(p["created"]).strftime("%Y-%m-%d %H:%M")
        xcode_badge = "  [Xcode]" if p["has_xcode"] else ""
        print(f"\n  {p['name']}{xcode_badge}")
        print(f"    Created : {created}")
        print(f"    Path    : {p['path']}")
    print(f"\n{'═' * 60}\n")


def _find_thread_id_path() -> str:
    """Place .thread_id next to the factory root so resume.py can find it."""
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent.parent / ".thread_id")


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
    elif repo_path:
        xcodeprojs = [f for f in os.listdir(repo_path) if f.endswith(".xcodeproj")] if os.path.isdir(repo_path) else []
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


def main():
    parser = argparse.ArgumentParser(
        prog="gemforge",
        description="GemForge — AI Product Factory",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    # gemforge new
    new_parser = subparsers.add_parser("new", help="Forge a new app from a raw idea")
    new_parser.add_argument("idea", help="Your raw idea, e.g. \"A minimalist HIIT timer\"")
    new_parser.add_argument(
        "--context",
        metavar="PATH",
        help="Optional: path to a directory of existing docs/code to incorporate",
        default=None,
    )

    # gemforge list
    list_parser = subparsers.add_parser("list", help="List all forged projects")
    list_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        metavar="N",
        help="Max projects to show (default: 20)",
    )

    args = parser.parse_args()

    if args.command == "new":
        cmd_new(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
