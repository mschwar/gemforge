# GemForge — LESSONS.md
**Lessons Learned — Updated on every D-Protocol Step 3**

**Last Updated:** 2026-02-24 19:58 MST

## Lessons from Phase 5 Bootstrap

- D-Protocol Step 1 (Read) is non-negotiable; skipping it on day one would have broken the foundation we are building.
- `cat > file << 'EOF' ... EOF` (single quotes) prevents unwanted shell expansion — use this pattern for all future file creation.
- Always force `cd /Users/mschwar/documents/github/gemforge` at the top of every block to guarantee root directory discipline.
- Starting with zero docs was actually ideal — clean slate, no migration debt.

## Lessons from earlier phases (backfilled)
- (Phases 1–4 already complete; will be expanded in future Step 3 updates)

### 2026-02-24 Discipline Protocol Bootstrap

- Successfully built and executed full 8-step Discipline Protocol on first attempt.
- `core/discipline/enforcer.py` implements `discipline_step` context manager, `@enforce_protocol` decorator, safe git helpers (subprocess), read_state, and audit logging — zero external dependencies.
- Proved that following the protocol from the very beginning creates perfect traceability and discipline.
- Key technical choice: Single-quoted heredoc (`<< 'EOF'`) to prevent variable expansion in all future file creation.
- Using `git add -A` + exact commit message format guarantees clean, professional history.

### 2026-02-24 Post-Bootstrap Cleanup
- audit.log was correctly modified in Step 8 after commit (expected). 
- Mini-cycle used to sync everything cleanly without breaking protocol.
- Git history now 100% consistent.

### 2026-02-24 Discipline Integration

- All 4 core entrypoints now demand the Discipline Protocol:
  - state.py: create_initial_pipeline_state + discipline_step
  - main.py + gemforge_cli.py: full @enforce_protocol decorator
  - pipeline.py: imports + entire graph build/compilation wrapped with discipline_step
- Used safe /tmp fixer script to bypass shell escaping (learned lesson: never put != in inline python -c)
- Every future run of GemForge will now print the D-Protocol banner and log to audit trail automatically.
- Zero breaking changes — backward compatible, venv-safe.
