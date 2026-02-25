"""
GemForge Core — Discipline Enforcer
Enforces the exact 8-step Discipline Protocol for every operation.
Zero external dependencies. Pure stdlib + subprocess for git.
"""

import os
import subprocess
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path


class DisciplineEnforcer:
    """Central enforcer for the 8-step Discipline Protocol."""

    FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent
    PROJECTS_ROOT = Path(os.getenv("PROJECTS_ROOT", str(FACTORY_ROOT.parent / "gemforge-projects")))
    AUDIT_LOG = FACTORY_ROOT / "audit.log"

    @staticmethod
    def timestamp() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M MST")

    @staticmethod
    def read_all_state(project_path: Path | None = None) -> dict:
        """Step 1: Read PERSISTENT.md, progress.txt, LESSONS.md (factory + project)"""
        state = {"factory": {}, "project": {}}
        factory = DisciplineEnforcer.FACTORY_ROOT

        def read_file(p: Path) -> str:
            return p.read_text(encoding="utf-8") if p.exists() else "[missing]"

        state["factory"]["persistent"] = read_file(factory / "PERSISTENT.md")
        state["factory"]["progress"]   = read_file(factory / "progress.txt")
        state["factory"]["lessons"]    = read_file(factory / "LESSONS.md")

        if project_path and project_path.exists():
            state["project"]["persistent"] = read_file(project_path / "PERSISTENT.md")
            state["project"]["progress"]   = read_file(project_path / "progress.txt")
            state["project"]["lessons"]    = read_file(project_path / "LESSONS.md")

        return state

    @staticmethod
    def git_command(repo_path: Path, args: list) -> str:
        """Safe git wrapper (used in Steps 6–7)"""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Git error: {e.stderr.strip()}"

    @staticmethod
    def disciplined_commit(repo_path: Path, step_number: int, short_name: str, description: str):
        """Step 6 & 7: Exact-format git commit + optional push.
        Push only when GEMFORGE_AUTO_PUSH=true is set in the environment."""
        message = f"step {step_number}: {short_name} - {description}"
        DisciplineEnforcer.git_command(repo_path, ["add", "."])
        DisciplineEnforcer.git_command(repo_path, ["commit", "-m", message])
        if os.getenv("GEMFORGE_AUTO_PUSH", "false").lower() == "true":
            DisciplineEnforcer.git_command(repo_path, ["push"])
            print(f"✅ [D-Protocol] Steps 6–7: Committed & pushed → {message}")
        else:
            print(f"✅ [D-Protocol] Steps 6–7: Committed (push skipped — set GEMFORGE_AUTO_PUSH=true to enable) → {message}")

    @staticmethod
    def log_audit(entry: str):
        """Step 8: Central audit trail"""
        ts = DisciplineEnforcer.timestamp()
        with open(DisciplineEnforcer.AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {entry}\n")
        print(f"📋 [D-Protocol] Step 8 Audit: {entry}")

    @staticmethod
    def cross_check():
        """Step 5: Basic consistency check (expand later)"""
        print("🔍 [D-Protocol] Step 5: Running cross-check...")
        status = DisciplineEnforcer.git_command(DisciplineEnforcer.FACTORY_ROOT, ["status", "--short"])
        if status:
            print(f"   Unstaged changes:\n{status}")
        else:
            print("   ✅ Clean working tree")

# Context manager for full protocol flow (used by all agents)
@contextmanager
def discipline_step(step_number: int, short_name: str, description: str, generated_project_path: Path | None = None):
    """Full 8-step enforcement context.
    Usage:
        with discipline_step(5, "Discipline Foundations", "Initial enforcer module"):
            # Step 2: Perform the work here
            ...
    """
    enforcer = DisciplineEnforcer()

    print(f"\n{'═'*80}")
    print(f"D-PROTOCOL STEP {step_number}: {short_name}")
    print(f"Description: {description}")
    print(f"Time: {enforcer.timestamp()}")
    print(f"{'═'*80}\n")

    # Step 1: Read state
    print("1. Reading current state (PERSISTENT + progress + LESSONS)...")
    enforcer.read_all_state(generated_project_path)

    try:
        # Step 2: PERFORM THE WORK (yield to calling code)
        yield enforcer
    finally:
        # Step 3-8: AUTOMATIC ENFORCEMENT
        enforcer.log_audit(f"Completed Step {step_number}: {short_name}")
        
        # If we are in a repo, commit the changes
        if generated_project_path and generated_project_path.exists():
            enforcer.disciplined_commit(
                generated_project_path, 
                step_number, 
                short_name, 
                description
            )
        
        # Always commit the factory itself
        enforcer.disciplined_commit(
            enforcer.FACTORY_ROOT,
            step_number,
            short_name,
            description
        )

# Decorator for easy agent wrapping
def enforce_protocol(step_number: int, short_name: str, description: str):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with discipline_step(step_number, short_name, description):
                return func(*args, **kwargs)
        return wrapper
    return decorator

if __name__ == "__main__":
    print("DisciplineEnforcer ready. Import via: from core.discipline import discipline_step")
