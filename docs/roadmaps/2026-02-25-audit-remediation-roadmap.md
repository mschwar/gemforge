# GemForge Audit Remediation Roadmap (Phased)

Date: 2026-02-25  
Source audit findings: GF-001 through GF-008 (staff-plus audit run on this repository)

## Objective
Close every confirmed audit issue with explicit engineering actions, objective gates, and commit-level checkpoints.

## Findings Index
- GF-001 (Crit): Deploy path can ship static placeholder instead of framework app.
- GF-002 (High): Project/thread identity collisions on reruns.
- GF-003 (High): QA and director gating allowed fail-open progression.
- GF-004 (High): Unbounded context ingestion for document auditor.
- GF-005 (Med): Cost/session persistence gap on refine path.
- GF-006 (Med): Code generation can write zero files and still report success.
- GF-007 (Med): Fail-open subprocess/git pathways reduce operational trust.
- GF-008 (Med): Test ergonomics and coverage gaps on pipeline-critical paths.

## Phase 1: Release Integrity Hardening (Immediate)
Scope: Lock release-critical correctness for deploy and approval gates.

### Actions
1. Preserve framework-native Vercel behavior; only apply static fallback to non-framework projects (GF-001).
2. Enforce fail-closed unknown-platform QA behavior (GF-003).
3. Remove director force-green fallback and require QA pass for approval (GF-003).
4. Add reliability regression tests for deploy and gate logic (GF-001, GF-003).

### Gates
- Gate P1-G1 (Deploy Correctness):
  - Framework project deploy path does not create/overwrite static fallback artifacts.
  - Evidence: automated test covering framework detection and artifact preservation.
- Gate P1-G2 (Approval Safety):
  - `tests_passed == False` always blocks `director_approved`.
  - Director rejection count no longer auto-flips approval to green.
  - Evidence: automated tests for both behaviors.
- Gate P1-G3 (Regression):
  - Test suite green in local CI command (`python -m pytest -q`).

### Exit Criteria
- All P1 gates pass.
- Merged commit hash recorded in this roadmap.

### Status
- Completed in commit `c270065132154a0125dac225be9aa153d77feca9`.
- Residual: monitor real-world deploy logs for edge frameworks beyond current detectors.

## Phase 2: Identity and State Safety
Scope: Remove run-collision risk and make cost/state accounting consistent across approval loops.

### Actions
1. Make project directory creation collision-safe (timestamp granularity + suffix loop) (GF-002).
2. Make `thread_id` generation collision-resistant (entropy suffix, not just idea prefix) (GF-002).
3. Persist/refinalize cost accounting after `resume refine` path (GF-005).
4. Add tests for path uniqueness and thread ID uniqueness semantics (GF-002, GF-005).

### Gates
- Gate P2-G1 (Filesystem Idempotency):
  - Two same-idea runs started on the same day produce distinct project directories.
  - Evidence: deterministic unit test with pre-created conflicting directory.
- Gate P2-G2 (Thread Safety):
  - Same-idea repeated invocations generate unique thread IDs unless user explicitly overrides thread.
  - Evidence: unit test validating uniqueness and format stability.
- Gate P2-G3 (Cost Integrity):
  - `resume refine` updates cost persistence path with same rigor as `resume approve`.
  - Evidence: unit/integration test asserting cost finalization side-effect.

### Exit Criteria
- All P2 gates pass with no regression in existing tests.
- Backward compatibility note added for legacy `.thread_id` lookup.

### Rollback Plan
- Keep old thread-ID lookup as fallback candidate for one release cycle.
- If cost persistence introduces duplicate writes, gate with idempotency token in session finalizer.

## Phase 3: Generation and Context Robustness
Scope: Bound LLM context costs and enforce minimum generation integrity guarantees.

### Actions
1. Add global budget to `bundle_context` (file count + byte budget + optional token estimate) (GF-004).
2. Rank/trim context inputs by relevance to `raw_idea` and key file patterns (GF-004).
3. Make code-orchestrator fail when generator write count is below threshold (GF-006).
4. Emit explicit structured progress/error entries when generation blocks are malformed (GF-006).
5. Add tests for bounded ingestion and zero-write generator failure semantics (GF-004, GF-006).

### Gates
- Gate P3-G1 (Context Bound):
  - Maximum bundled context size is enforced and test-validated.
  - Evidence: test with oversized synthetic tree proving deterministic truncation.
- Gate P3-G2 (Cost Guardrail):
  - Context builder reports dropped file count and estimated budget usage in logs/state.
  - Evidence: snapshot test or structured output assertion.
- Gate P3-G3 (Generation Integrity):
  - If any required generator writes `0` files, node exits with failure signal and halts forward progression.
  - Evidence: test with mocked malformed LLM output.

### Exit Criteria
- P3 gates pass and no silent-success path remains for empty generation outputs.
- Cost/cap parameters documented in README + `.env.example`.

### Rollback Plan
- Feature-flag strict generation thresholds for one release if false positives appear on edge prompts.

## Phase 4: Operability and Failure Semantics
Scope: Remove ambiguous fail-open behavior and make operator intervention points explicit.

### Actions
1. Classify subprocess actions into `critical` vs `non-critical` and enforce fail policy per class (GF-007).
2. Convert critical failures (git bootstrap/publish, required build steps) from warn-and-continue to actionable failure states (GF-007).
3. Add structured error envelope to pipeline state (`error_code`, `error_stage`, `operator_action`) for downstream reporting (GF-007).
4. Update CLI final report to distinguish success, partial success, and blocked/manual intervention outcomes (GF-007).
5. Add tests for publish failure and critical command failure routing (GF-007).

### Gates
- Gate P4-G1 (Critical Stop):
  - Simulated critical git/publish failure prevents false success messaging.
  - Evidence: integration-style unit test with mocked subprocess failure.
- Gate P4-G2 (Operator Clarity):
  - Final CLI output includes clear next action when blocked.
  - Evidence: snapshot/assertion test on report content.
- Gate P4-G3 (State Explainability):
  - Failure metadata is persisted and visible for dashboard or future API surfaces.
  - Evidence: state assertion at end of failed run.

### Exit Criteria
- No critical pipeline failure can be emitted as mission-complete.
- All new error codes documented in an operator runbook section.

### Rollback Plan
- Keep legacy warn-only path behind temporary env flag during one stabilization cycle.

## Phase 5: Test Fidelity, DX, and AI-Native Maintainability
Scope: Close coverage and ergonomics gaps so human and AI contributors can safely evolve the system.

### Actions
1. Standardize test invocation so `pytest` and `python -m pytest` both work from repo root (GF-008).
2. Add integration-focused tests for `new → review pause → resume approve/refine` critical flow (GF-008).
3. Add tests for deploy/publish failure-state reporting and gating interactions (GF-007, GF-008).
4. Split orchestration concerns into stage modules (`pipeline/stages/*.py`) to lower blast radius of edits (cross-cutting).
5. Add concise architectural map and state-transition docs for AI coding assistants (cross-cutting AI-DX).

### Gates
- Gate P5-G1 (Command Ergonomics):
  - `pytest -q` passes in a clean venv without manual `PYTHONPATH` export.
  - Evidence: CI job running plain pytest command.
- Gate P5-G2 (Flow Coverage):
  - Critical pipeline flow has integration coverage for pause/resume and error branches.
  - Evidence: tests proving gate transitions and final state correctness.
- Gate P5-G3 (Cognitive Load Reduction):
  - Orchestrator size and responsibilities are reduced with stage-level module boundaries.
  - Evidence: architecture diff and module-level ownership map.

### Exit Criteria
- Critical-path tests are mandatory in CI.
- New contributors can run and validate full local flow from README steps without path workarounds.

## Traceability Matrix (All Findings Covered)
| Finding | Phase(s) | Closure Mechanism |
|---|---|---|
| GF-001 | Phase 1 | Framework-aware deploy path; static fallback only for non-framework repos |
| GF-002 | Phase 2 | Unique project path/thread ID generation + collision tests |
| GF-003 | Phase 1 | Fail-closed QA + no force-green director behavior |
| GF-004 | Phase 3 | Context bundling budgets and relevance-based trimming |
| GF-005 | Phase 2 | Refine-path session/cost persistence parity |
| GF-006 | Phase 3 | Minimum write-count enforcement in code generation |
| GF-007 | Phase 4 (+5) | Critical/non-critical failure semantics + operator-visible errors |
| GF-008 | Phase 5 | Test command ergonomics + critical-flow coverage expansion |

## Commit Checkpoints (Per Major Phase Step)
- Phase 1 roadmap checkpoint: `81d2198`
- Phase 2 roadmap checkpoint: `d2793fa`
- Phase 3 roadmap checkpoint: `d51716a`
- Phase 4 roadmap checkpoint: `6f6b7e2`
