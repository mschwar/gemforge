# 02_remediation_backlog

## Top 3 Remediation Priorities

### 1. Fix [F01]: Fail-Fast I/O & Error State Propagation
The current silent swallowing of `PermissionError` is a critical reliability risk. We must replace `except PermissionError: pass` with explicit state updates that mark the pipeline as `blocked`.

*   **Gate 1: Tests:** Create `tests/test_io_failures.py`. Mock `ProjectSandbox.safe_write` to raise `PermissionError`. Verify `PipelineState` has `pipeline_status="blocked"` and `error_code="PERMISSION_ERROR"`.
*   **Gate 2: Implementation:** In `pipeline.py` and `core/repair/agentic_loop.py`, replace all instances of `except PermissionError: pass` with a unified error handler that updates `state["pipeline_status"] = "blocked"` and `state["error_code"] = "IO_PERMISSION_FAILURE"`.
*   **Gate 3: Validation:** Run `pytest tests/test_io_failures.py`. Ensure the pipeline stops and the `operator_action` field contains instructions for the user (e.g., "Check project directory permissions").
*   **Gate 4: Fallback:** For non-critical writes (like `DIRECTOR_REVIEW.md`), allow the pipeline to continue but log a warning to `progress_log`. For critical writes (`ARCHITECTURE.md`, `source_code`), the pipeline must block.

### 2. Fix [F02]: Modular Pipeline Node Refactoring (Phase 1)
Extracting node logic from `pipeline.py` to reduce cognitive load and improve testability.

*   **Gate 1: Tests:** Create unit tests for at least 3 nodes (e.g., `vision_polisher_node`, `architecture_node`) in a new file `tests/test_nodes_isolated.py` by importing them from their new modular home.
*   **Gate 2: Implementation:** Create `core/pipeline_stages/nodes/`. Move at least the first 5 nodes (`document_auditor_node`, `vision_polisher_node`, `human_review_node`, `ruthless_interrogator_node`, `bootstrapper_node`) into individual files (e.g., `core/pipeline_stages/nodes/vision.py`). Update `pipeline.py` to import these functions.
*   **Gate 3: Validation:** Run `pytest tests/test_nodes_isolated.py` and a full pipeline smoke test: `python -m pytest tests/test_blueprint_01_runtime.py`.
*   **Gate 4: Fallback:** Maintain the `pipeline.py` node definitions as simple thin wrappers around the new modular imports for a "strangler" migration period.

### 3. Fix [F04]: Dynamic Strategy Switching in Agentic Repair
Instead of stalling on identical patches, the Surgeon should be forced to change strategy (e.g., "Think step-by-step," "Check project root for missing configs," "Expand search radius").

*   **Gate 1: Tests:** Update `tests/test_reliability_guards.py`. Mock the Surgeon to return the same patch twice. Verify the second call to `repair_node` includes a `strategy_prompt` mentioning the previous identical patch.
*   **Gate 2: Implementation:** In `core/repair/agentic_loop.py`, when a `patch_hash` collision is detected, instead of returning `repair_status="stalled"`, increment a `stall_counter` and re-invoke `cost_aware_invoke` with an "Emergency Diversification Prompt" that explicitly forbids the previous patch.
*   **Gate 3: Validation:** Run a simulated repair loop using `python core/repair/agentic_loop.py` (if it has a main block) or via a new test case.
*   **Gate 4: Fallback:** If diversification fails after 2 additional attempts, only then set `repair_status="stalled_diversity_exhausted"` and trigger `human_review`.

---
Audit complete. Artifacts written to disk. Please add, commit, and hash the .ascension/audit/ directory to version control, then start a new chat with the Delivery Lead Agent, pointing it to 02_remediation_backlog.md to begin execution.
