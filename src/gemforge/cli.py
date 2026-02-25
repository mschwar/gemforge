#!/usr/bin/env python
import hashlib
import signal
import sys
import time
from pathlib import Path
from uuid import uuid4

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
from core.runtime.event_logger import event_logger # noqa: E402
from core.build.taint_manager import taint_manager # noqa: E402
from core.build.cache import build_cache # noqa: E402
from core.runtime.logging import setup_logging # noqa: E402

# Initialize structured logging early
setup_logging()

# ---------------------------------------------------------------------------
# SIGINT handler — persists cost to DB before exit so no session data is lost
# ---------------------------------------------------------------------------
def _sigint_handler(signum, frame):
    print("\n\n⚠️  Interrupted — saving cost data before exit...")
    try:
        from tools.cost_tracker import cost_tracker
        cost_tracker.finalize_session()
        print(f"   💰 Partial session: ${cost_tracker.total_cost:.4f} | Calls: {cost_tracker.calls}")
    except Exception:
        pass
    sys.exit(130)  # conventional exit code for SIGINT (128 + 2)


# ---------------------------------------------------------------------------
# Thread-ID helpers (shared by cmd_new and cmd_resume)
# ---------------------------------------------------------------------------
def _find_thread_id_path() -> str:
    """Canonical .thread_id location — repo root, shared with resume.py."""
    return str(_REPO_ROOT / ".thread_id")


def _thread_id_candidates() -> list:
    root = _REPO_ROOT
    # Include one level up for backward-compat with very early sessions.
    return [root / ".thread_id", root.parent / ".thread_id"]


def _load_thread_id(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    existing = [p for p in _thread_id_candidates() if p.exists() and p.read_text().strip()]
    if existing:
        newest = max(existing, key=lambda p: p.stat().st_mtime)
        return newest.read_text().strip()
    print("❌  No active session found and no thread-id provided.")
    print("    Run 'gemforge new \"your idea\"' first, then come back here.")
    sys.exit(1)


def _build_thread_id(raw_idea: str) -> str:
    """Create collision-resistant thread IDs while keeping a readable slug prefix."""
    slug = "".join(
        c for c in raw_idea[:60].replace(" ", "-").replace("/", "")
        if c.isalnum() or c in "-_"
    ).strip("-_") or "idea"

    # Include both random and time entropy to avoid collisions across rapid retries.
    entropy = f"{uuid4().hex[:8]}-{time.time_ns()}"
    suffix = hashlib.sha1(entropy.encode("utf-8")).hexdigest()[:8]
    return f"gem-{slug}-{suffix}"


# ---------------------------------------------------------------------------
# Shared reporting helpers
# ---------------------------------------------------------------------------
def _finalize_and_report(result: dict):
    """Persist cost and print the final report after any pipeline resume."""
    from tools.cost_tracker import cost_tracker
    cost_tracker.finalize_session()
    cumulative = cost_tracker.get_cumulative_cost()
    print(f"\n   💰 Session: ${cost_tracker.total_cost:.4f} | Tokens: {cost_tracker.total_tokens:,} | Calls: {cost_tracker.calls}")
    print(f"   📊 All-time total: ${cumulative:.4f}")

    if result.get("approval_status") == "pending":
        print("\n⏸️  Pipeline paused for another review gate.")
        print("   gemforge resume approve")
        print("   gemforge resume refine \"Your feedback\"")
    else:
        _print_final_report(result)


def _print_final_report(result: dict):
    repo_path = result.get("repo_path", "")
    live_url = result.get("live_url")
    pipeline_status = result.get("pipeline_status", "success")
    error_code = result.get("error_code")
    error_stage = result.get("error_stage")
    operator_action = result.get("operator_action")

    if pipeline_status == "blocked":
        banner = "  ⛔  GEMFORGE MISSION BLOCKED"
    elif pipeline_status == "partial":
        banner = "  ⚠️  GEMFORGE MISSION PARTIAL"
    else:
        banner = "  🎉  GEMFORGE MISSION COMPLETE"

    print("\n" + "═" * 80)
    print(banner)
    print("═" * 80)
    print(f"  Project:  {repo_path or 'N/A'}")
    print(f"  Live URL: {live_url or 'Native project — open in Xcode/Android Studio'}")
    if error_code:
        print(f"  Error:    {error_code} ({error_stage or 'unknown stage'})")
    if operator_action:
        print(f"  Action:   {operator_action}")
    print()
    print("  What to do next:")
    if repo_path:
        print(f"     cd {repo_path}")
    if live_url:
        print(f"     open {live_url}")
    elif operator_action:
        print(f"     {operator_action}")
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
    if pipeline_status == "blocked":
        print("  ❌ Manual intervention required before release.")
    elif pipeline_status == "partial":
        print("  ⚠️ Release is partially complete; address the action item(s) above.")
    else:
        print("  ✅ Your app is ready. Go ship it.")
    print("═" * 80)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
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
    signal.signal(signal.SIGINT, _sigint_handler)

    thread_id = _build_thread_id(raw_idea)

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
        print("   gemforge resume approve")
        print("   gemforge resume refine \"Your feedback\"")
        return

    _print_final_report(result)


def cmd_resume(args):
    from langgraph.types import Command

    signal.signal(signal.SIGINT, _sigint_handler)
    thread_id = _load_thread_id(getattr(args, "thread", None))
    config = {"configurable": {"thread_id": thread_id}}

    if args.action == "approve":
        print(f"   Resuming thread: {thread_id}")
        print("✅ Approved — continuing pipeline...")
        result = get_pipeline_app().invoke(Command(resume={"action": "approved"}), config)
        _finalize_and_report(result)

    elif args.action == "refine":
        feedback = args.feedback
        print(f"   Resuming thread: {thread_id}")
        print(f"🔄 Refining with feedback: {feedback}")
        result = get_pipeline_app().invoke(Command(resume={"action": "rejected", "feedback": feedback}), config)
        print("\n" + "─" * 80)
        print("  REFINED VISION")
        print("─" * 80)
        print(result.get("polished_vision", ""))
        print("─" * 80)
        print("\n⏸️  Review the refined vision, then:")
        print("   gemforge resume approve")
        print("   gemforge resume refine \"More feedback\"")
        _finalize_and_report(result)


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


def cmd_runs_list(args):
    runs = event_logger.get_recent_runs(limit=args.limit)
    if not runs:
        print("No run events found.")
        return

    print(f"\n{'═' * 60}")
    print(f"  🏃  Recent GemForge Runs")
    print(f"{'═' * 60}")
    for run_id in runs:
        print(f"  - {run_id}")
    print(f"{'═' * 60}\n")


def cmd_runs_tail(args):
    import time
    run_id = args.run_id
    seen_event_ids = set()

    print(f"\n{'═' * 60}")
    print(f"  🎬  Tailing run: {run_id}")
    print(f"  (Ctrl+C to stop)")
    print(f"{'═' * 60}")

    try:
        while True:
            events = event_logger.get_run_events(run_id)
            for e in events:
                if e["event_id"] not in seen_event_ids:
                    ts = datetime.datetime.fromisoformat(e["created_at"]).strftime("%H:%M:%S")
                    status_icon = "🟢" if "completed" in e["event_type"] else "🟡" if "started" in e["event_type"] else "🔴"
                    print(f"  [{ts}] {status_icon} {e['step_id']:<20} | {e['event_type']}")
                    seen_event_ids.add(e["event_id"])
            
            if not args.follow:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{'═' * 60}")
        print("  Stopped tailing.")
        print(f"{'═' * 60}\n")


def cmd_build_taint(args):
    run_id = args.run_id
    node_id = args.node_id
    reason = args.reason
    taint_manager.taint_node(run_id, node_id, reason)
    print(f"   ✅ Node '{node_id}' and all downstream dependents tainted for run {run_id}.")


def cmd_build_status(args):
    import sqlite3
    run_id = args.run_id
    
    print(f"\n{'═' * 60}")
    print(f"  🏗️  Build Status for run: {run_id}")
    print(f"{'═' * 60}")
    
    with sqlite3.connect(taint_manager.db_path, timeout=30) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT node_id, reason, created_at FROM tainted_nodes WHERE run_id = ?", (run_id,))
        tainted = cur.fetchall()
        
    if not tainted:
        print("   ✅ No nodes are currently tainted. Everything is up to date.")
    else:
        print(f"   🚩 Found {len(tainted)} stale (tainted) nodes:")
        for row in tainted:
            print(f"     - {row['node_id']:<20} | Reason: {row['reason']:<20} | Stale since: {row['created_at']}")
            
    print(f"{'═' * 60}\n")


def cmd_doctor(args):
    import subprocess
    import platform

    print(f"\n{'═' * 60}")
    print("  🩺  GemForge Doctor — Environmental Health Check")
    print(f"{'═' * 60}")

    # 1. API Key
    if os.getenv("ANTHROPIC_API_KEY"):
        print("  ✅ ANTHROPIC_API_KEY is set.")
    else:
        print("  ❌ ANTHROPIC_API_KEY is missing.")

    # 2. Python version
    py_ver = platform.python_version()
    if sys.version_info >= (3, 12):
        print(f"  ✅ Python version: {py_ver}")
    else:
        print(f"  ❌ Python version: {py_ver} (GemForge requires 3.12+)")

    # 3. Git
    try:
        git_ver = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()
        print(f"  ✅ {git_ver}")
    except Exception:
        print("  ❌ git is not installed.")

    # 4. Node / NPM
    try:
        node_ver = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
        print(f"  ✅ Node: {node_ver}")
        npm_ver = subprocess.run(["npm", "--version"], capture_output=True, text=True).stdout.strip()
        print(f"  ✅ NPM:  v{npm_ver}")
    except Exception:
        print("  ❌ Node.js / NPM is not installed.")

    # 5. Apple/iOS specific (if on Darwin)
    if platform.system() == "Darwin":
        try:
            xc_ver = subprocess.run(["xcodebuild", "-version"], capture_output=True, text=True).stdout.strip().splitlines()[0]
            print(f"  ✅ {xc_ver}")
        except Exception:
            print("  ⚠️ xcodebuild not found (iOS development will be unavailable).")

        try:
            xcg_path = subprocess.run(["which", "xcodegen"], capture_output=True, text=True).stdout.strip()
            if xcg_path:
                print("  ✅ xcodegen is installed.")
            else:
                print("  ❌ xcodegen is missing. (Install with: brew install xcodegen)")
        except Exception:
            print("  ❌ xcodegen check failed.")

    print(f"{'═' * 60}\n")


# ---------------------------------------------------------------------------
# Argparse entry point
# ---------------------------------------------------------------------------
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

    # gemforge resume {approve,refine}
    resume_parser = subparsers.add_parser("resume", help="Approve or refine after a human review gate")
    resume_sub = resume_parser.add_subparsers(dest="action", metavar="<action>")

    approve_parser = resume_sub.add_parser("approve", help="Approve the polished vision and continue")
    approve_parser.add_argument(
        "--thread", metavar="THREAD_ID", default=None,
        help="Thread ID (auto-detected from last session if omitted)",
    )

    refine_parser = resume_sub.add_parser("refine", help="Send feedback and re-polish the vision")
    refine_parser.add_argument("feedback", help="Your refinement feedback")
    refine_parser.add_argument(
        "--thread", metavar="THREAD_ID", default=None,
        help="Thread ID (auto-detected from last session if omitted)",
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

    # gemforge runs
    runs_parser = subparsers.add_parser("runs", help="Manage and inspect runs")
    runs_sub = runs_parser.add_subparsers(dest="runs_action", metavar="<action>")

    runs_list_parser = runs_sub.add_parser("list", help="List recent runs")
    runs_list_parser.add_argument("--limit", type=int, default=10, help="Max runs to show")

    runs_tail_parser = runs_sub.add_parser("tail", help="Tail events for a specific run")
    runs_tail_parser.add_argument("run_id", help="The run ID to tail")
    runs_tail_parser.add_argument("-f", "--follow", action="store_true", help="Follow the event stream")

    # gemforge build {status, taint}
    build_parser = subparsers.add_parser("build", help="Manage deterministic build state and cache")
    build_sub = build_parser.add_subparsers(dest="build_action", metavar="<action>")

    build_status_parser = build_sub.add_parser("status", help="Show build status (stale nodes) for a run")
    build_status_parser.add_argument("run_id", help="The run ID to check")

    build_taint_parser = build_sub.add_parser("taint", help="Manually mark a node as stale")
    build_taint_parser.add_argument("run_id", help="The run ID")
    build_taint_parser.add_argument("node_id", help="The node ID to taint")
    build_taint_parser.add_argument("--reason", default="manual_taint", help="Reason for tainting")

    # gemforge doctor
    subparsers.add_parser("doctor", help="Check system prerequisites and environment")

    args = parser.parse_args()

    if args.command == "new":
        cmd_new(args)
    elif args.command == "resume":
        if not args.action:
            resume_parser.print_help()
            sys.exit(1)
        cmd_resume(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "runs":
        if args.runs_action == "list":
            cmd_runs_list(args)
        elif args.runs_action == "tail":
            cmd_runs_tail(args)
        else:
            runs_parser.print_help()
            sys.exit(1)
    elif args.command == "build":
        if args.build_action == "status":
            cmd_build_status(args)
        elif args.build_action == "taint":
            cmd_build_taint(args)
        else:
            build_parser.print_help()
            sys.exit(1)
    elif args.command == "doctor":
        cmd_doctor(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
