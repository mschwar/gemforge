# Engineering Roadmap: Audit Remediation & System Hardening (2026-02-25)

This roadmap outlines the systematic approach to resolving the findings identified in the Principal Engineering Audit.

## Phase 1: Reliability & Safety (Immediate - 24-48 Hours)
*Goal: Prevent data corruption and system hangs.*

- [ ] **[FINDING-01] Implement Thread-Safety in `CostTracker`:** 
    - Add `threading.Lock` to the `CostTracker` class.
    - Wrap `track_call` and `finalize_session` in context managers to ensure atomic updates.
- [ ] **[FINDING-02] Harden Remote Cache IO:**
    - Introduce `botocore.config.Config` with `connect_timeout=2` and `read_timeout=3`.
    - Wrap S3 `get_object` and `put_object` in `try/except` blocks to ensure fail-closed (local only) behavior on network issues.
- [ ] **[FINDING-05] SwarmFactory Temp Cleanup:**
    - Add a cleanup method to `SwarmFactory` to delete temporary prompt files in `agents/temporary/` after a project is successfully forged or on error.

## Phase 2: System Integrity & CI/CD Robustness (Short-Term - 1 Week)
*Goal: Eliminate host mutations and environment brittleness.*

- [ ] **[FINDING-03] Remove Host Mutations:**
    - Delete `install_xcodegen` from `tools/project_tools.py`.
    - Update `generate_xcode_project` to check for `xcodegen` existence using `which` and raise a `CommandFailure` with actionable instructions if missing.
- [ ] **[FINDING-04] Dynamic Environment Detection:**
    - In `tools/executor_tools.py`, replace hardcoded `"iPhone 16"` with a utility that queries `xcrun simctl list devices --json` and selects the first available `booted` or `shutdown` simulator.
    - Parameterize `npm` and `xcodebuild` versions via environment variables with sensible defaults.
- [ ] **Enhanced Prerequisite Checks:**
    - Implement a `gemforge doctor` command to verify all local dependencies (`git`, `node`, `xcodebuild`, `xcodegen`) before starting a forge.

## Phase 3: Architectural Refactoring & Observability (Medium-Term - 1 Month)
*Goal: Align with functional paradigms and improve production readiness.*

- [ ] **Functional Cost Tracking:**
    - Refactor `PipelineState` to include `total_tokens` and `total_cost`.
    - Use LangGraph `operator.add` to aggregate these values across parallel nodes, removing the need for the `CostTracker` singleton entirely.
- [ ] **Structured Logging & Telemetry:**
    - Migrate from `print()` statements to a structured `logging` library (e.g., `structlog` or `json-logging`).
    - Ensure all events published to `event_bus` are captured in a machine-readable format for dashboarding.
- [ ] **Test Fidelity & Virtualization:**
    - Investigate using Docker for web/backend test execution to eliminate "works on my machine" issues in CI.
    - Research `xcresult` parsing for better iOS test failure diagnostics in the `director_node`.
- [ ] **Agentic Repair Hardening:**
    - Implement token-window-aware context truncation in the `repair_node` to prevent context-length errors during long repair loops.
