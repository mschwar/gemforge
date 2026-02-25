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
