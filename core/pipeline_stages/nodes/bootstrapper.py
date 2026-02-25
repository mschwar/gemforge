import json
from pathlib import Path
from datetime import datetime, timezone
from core.runtime.sandbox import ProjectSandbox
from tools.file_tools import create_project_structure
from core.build.hasher import calculate_dir_hash, calculate_file_hash
from core.runtime.errors import handle_io_error
from state import PipelineState
from .utils import _index_files, parse_and_save_docs

def bootstrapper_node(state: PipelineState):
    print("🔨 3. Bootstrapper creating REAL project...")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    repo_path = create_project_structure(gem_name)
    sandbox = ProjectSandbox(repo_path)

    # Write the Staff Audit if it exists
    audited = state.get("audited_context")
    if audited:
        try:
            p = sandbox.safe_write("STAFF_AUDIT.md", audited)
            print("   → STAFF_AUDIT.md saved to repo")
            # Index the staff audit
            _index_files(state["run_id"], gem_name, [p], "audit")
        except PermissionError as e:
            return handle_io_error(state, e, "bootstrapper (audit)")

    # Write canonical docs now that the folder exists
    raw_output = state.get("canonical_docs", {}).get("_raw_output", "")
    if raw_output:
        try:
            saved, saved_paths = parse_and_save_docs(raw_output, sandbox)
            canonical_docs = saved if saved else {"INTERROGATION.md": raw_output[:200]}
            if not saved:
                try:
                    p = sandbox.safe_write("INTERROGATION.md", raw_output)
                    saved_paths = [p]
                except PermissionError as e:
                    return handle_io_error(state, e, "bootstrapper (interrogation)")
            
            # Index canonical docs
            _index_files(state["run_id"], gem_name, saved_paths, "spec")
        except PermissionError as e:
            return handle_io_error(state, e, "bootstrapper (canonical docs)")
    else:
        canonical_docs = {}

    print(f"   → Project ready: {repo_path}")
    
    # 4. Generate Build Manifest (Phase 0)
    manifest = {
        "project_name": gem_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bootstrap_hash": calculate_dir_hash(Path(repo_path)),
        "files": {
            str(p.relative_to(repo_path)): calculate_file_hash(p)
            for p in Path(repo_path).glob("*") if p.is_file() and not p.name.startswith(".")
        }
    }
    try:
        sandbox.safe_write("BUILD_MANIFEST.json", json.dumps(manifest, indent=2))
    except PermissionError as e:
        # Non-critical, just log warning
        handle_io_error(state, e, "bootstrapper (manifest)", critical=False)

    return {
        "repo_path": repo_path,
        "repo_created": True,
        "canonical_docs": canonical_docs,
        "progress_log": [f"✅ Repo + docs at {repo_path}"],
    }
