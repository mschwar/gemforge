import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from langchain_core.messages import HumanMessage, SystemMessage

from core.llm import cost_aware_invoke, load_prompt
from core.memory.retriever import semantic_retriever
from core.repair.signature import build_failure_signature
from core.build.hasher import calculate_string_hash
from core.runtime.sandbox import ProjectSandbox
from tools.executor_tools import parse_and_save_generated_code, run_tests
from tools.file_tools import write_file

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "checkpoints.db"

def repair_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Agentic repair loop: diagnoses failure, proposes patch, verifies.
    
    Supports multiple attempts with strategy switching and safety caps.
    """
    repo_path = state.get("repo_path")
    platform = state.get("selected_platform", "web")
    test_report = state.get("test_report", "")
    run_id = state.get("run_id", "unknown")
    repair_count = state.get("repair_count", 0) + 1
    
    if not repo_path or not test_report:
        print("   ⚠️ Repair skipped: missing repo_path or test_report")
        return {"repair_status": "skipped"}

    sandbox = ProjectSandbox(repo_path)
    max_attempts = int(os.getenv("GEMFORGE_AUTO_REPAIR_MAX_ATTEMPTS", "3"))
    write_cap = int(os.getenv("GEMFORGE_AUTO_REPAIR_WRITE_CAP", "8"))

    print(f"   🛠️ [REPAIR] Attempt {repair_count}/{max_attempts}...")

    # 1. Build Failure Signature
    raw_error = state.get("test_details", test_report)
    signature = build_failure_signature(platform, "test-runner", raw_error)
    print(f"   🛠️ [REPAIR] Diagnosis: {signature}")

    # 2. Strategy Selection
    strategy = "direct_fix"
    strategy_prompt = ""
    if repair_count > 1:
        strategy = "alternative_approach"
        strategy_prompt = (
            f"\nYour previous {repair_count-1} attempt(s) did not fix the issue. "
            "Please try a DIFFERENT strategy. If you tried fixing the implementation, "
            "check the types or the test setup. Avoid repeating previous patches."
        )

    # 3. Retrieve Semantic Context
    retrieved_context = ""
    try:
        hits = semantic_retriever.search(f"{signature}\n{test_report}", k=5)
        if hits:
            retrieved_context = "\n### RELEVANT MEMORY CHUNKS:\n"
            for h in hits:
                retrieved_context += f"\n- {h['text']}\n"
    except Exception as e:
        print(f"   ⚠️ Repair RAG failed: {e}")

    # 4. Invoke Surgeon
    prompt = load_prompt("22_iteration_surgeon.md")
    
    # Gather failing file content
    failing_file_content = ""
    if "path=" in signature and "|path=n/a" not in signature:
        failing_path_str = signature.split("path=")[-1]
        try:
            content = sandbox.safe_read(failing_path_str)
            if content:
                failing_file_content = f"\n### FAILING FILE CONTENT ({failing_path_str}):\n{content}"
        except PermissionError: pass

    user_content = (
        f"PROJECT_PATH: {repo_path}\n"
        f"PLATFORM: {platform}\n"
        f"FAILURE_REPORT:\n{test_report}\n"
        f"RAW_STDOUT_STDERR:\n{raw_error[:2000]}\n"
        f"{failing_file_content}\n"
        f"{retrieved_context}\n"
        f"{strategy_prompt}\n"
        f"SAFETY LIMIT: Do not modify more than {write_cap} files."
        "\n\nPlease provide a patch to fix this failure."
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=user_content)]
    print(f"   🧪 [REPAIR] Surgeon is thinking (Strategy: {strategy})...")
    response = cost_aware_invoke(messages)
    
    # 4b. Novelty Check (Fix 3)
    patch_content = response.content.strip()
    patch_hash = calculate_string_hash(patch_content)
    history = state.get("repair_history", [])
    
    if any(h.get("patch_hash") == patch_hash for h in history):
        print("   ⚠️ [REPAIR] Novelty check failed: Surgeon proposed identical patch. Aborting to prevent loop.")
        return {
            "tests_passed": False,
            "repair_status": "stalled_identical_patch",
            "progress_log": ["❌ Agentic Repair stalled: Surgeon proposed identical patch"]
        }

    # 5. Apply Patch (with safety cap check)
    print(f"   🩹 [REPAIR] Applying patches...")
    written_paths = parse_and_save_generated_code(sandbox, response.content)
    
    if len(written_paths) > write_cap:
        print(f"   ⚠️ [REPAIR] Safety violation: modified {len(written_paths)} files, cap is {write_cap}.")

    # 6. Verify Fix
    print(f"   🧪 [REPAIR] Verifying fix...")
    test_result = run_tests(repo_path, platform)
    
    # 7. Log Attempt & Generate Report
    attempt_id = str(uuid.uuid4())
    status = "succeeded" if test_result["success"] else "failed"
    
    attempt_record = {
        "attempt_id": attempt_id,
        "run_id": run_id,
        "signature": signature,
        "patch_hash": patch_hash,
        "attempt_number": repair_count,
        "strategy": strategy,
        "files_modified": [str(p.relative_to(sandbox.root)) for p in written_paths],
        "status": status,
        "test_report": test_result["report"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # SQLite Ledger
    with sqlite3.connect(str(_DB_PATH), timeout=30) as conn:
        conn.execute(
            "INSERT INTO repair_attempts (attempt_id, run_id, failure_signature, attempt_number, strategy, candidate_patch_summary, status, tests_report, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                attempt_id, run_id, signature, repair_count, strategy, 
                f"Modified {len(written_paths)} files: {', '.join(attempt_record['files_modified'])}",
                status, test_result["report"], attempt_record["timestamp"]
            )
        )
        conn.commit()

    # Disk Artifacts
    report_md = f"# Repair Report - Attempt {repair_count}\n\n"
    report_md += f"- **Status**: {status.upper()}\n"
    report_md += f"- **Signature**: `{signature}`\n"
    report_md += f"- **Strategy**: {strategy}\n"
    report_md += f"- **Files Modified**: {len(written_paths)}\n"
    for p in attempt_record["files_modified"]:
        report_md += f"  - `{p}`\n"
    report_md += f"\n## Test Result\n{test_result['report']}\n"
    
    try:
        sandbox.safe_write(f"REPAIR_REPORT_A{repair_count}.md", report_md)
    except PermissionError: pass

    # Index successful repairs
    if status == "succeeded" and written_paths:
        from core.memory.semantic_index import semantic_indexer
        for p in written_paths:
            try:
                semantic_indexer.index_file(run_id, Path(repo_path).name, p, "repair")
            except Exception:
                pass

    print(f"   ✅ [REPAIR] Verdict: {test_result['report']}")
    
    new_history = state.get("repair_history", []) + [attempt_record]
    
    return {
        "tests_passed": test_result["success"],
        "test_report": test_result["report"],
        "test_details": test_result.get("details", ""),
        "repair_count": repair_count,
        "repair_history": new_history,
        "repair_status": status if test_result["success"] else ("max_attempts_reached" if repair_count >= max_attempts else "failed"),
        "progress_log": [f"🛠️ Agentic Repair {status} (Attempt {repair_count}): {test_result['report']}"]
    }
