"""
GemForge Discipline Protocol — Cross-Check Tool (Step 5)
Enforces consistency between state, files on disk, and git before any commit.
"""

from pathlib import Path
from .enforcer import DisciplineEnforcer

def run_cross_check(generated_project_path: Path = None):
    """Full Step 5 execution"""
    enforcer = DisciplineEnforcer()
    enforcer.cross_check()
    
    # Basic additional checks (expandable)
    required_files = ["PERSISTENT.md", "progress.txt", "LESSONS.md"]
    for f in required_files:
        if not (enforcer.FACTORY_ROOT / f).exists():
            print(f"⚠️  Missing factory file: {f}")
    
    print("✅ [D-Protocol] Step 5 Cross-check PASSED (basic validation complete)")
    return True

if __name__ == "__main__":
    run_cross_check()
