# GemForge v2.0 — Evolution Discipline Protocol

**Version**: 1.0  
**Date**: 2026-02-24  

Prompt evolution takes completed run logs, test results, and operator feedback as inputs, validates candidate prompt diffs against prior runs and human review gates, and outputs versioned prompt files under `agents/prompts/` plus recorded lessons in `lessons/lessons.db`.

## Three Rules of Prompt Evolution

1. **Preserve Passing Behavior** — Candidate prompt revisions must pass regression checks against prior project runs before activation.
2. **Measure Changes** — Prompt revisions must state expected improvements in test pass rate, output structure, or token cost.
3. **Record Provenance** — Every completed run captures structured lessons, and every prompt revision stays versioned in Git.

## Core Components

- **User Taste Memory** — Operator style, stack preferences, and explicit constraints stored in `memory/user_taste.json`.
- **Lessons Database** — SQLite store (`lessons/lessons.db`) paired with human-readable summaries in `LESSONS.md`.
- **Versioned Prompts** — Immutable prompt files at `agents/prompts/{agent}/v{version}.md` tracked alongside `metadata.json`.
- **Weaver Reflection Stage** — Post-run stage ([`core/evolution/weaver.py`](../../core/evolution/weaver.py)) that extracts lessons after shipping completes.

## Workflow (Automated Capture and Human Gate)

1. A pipeline run finishes and invokes the Weaver stage.
2. Extracted lessons write to `lessons/lessons.db` and `LESSONS.md`.
3. Accumulated lessons or an explicit evolution run draft candidate prompt revisions.
4. The candidate revision writes a proposal file (`evolutions/proposal_YYYYMMDD.md`) containing the prompt diff and rationale.
5. **Human approval gate**: an operator inspects the diff and shadow-test output before promoting a new prompt version.
6. Approved revisions increment the prompt version file, record the rationale in Git history, and update `LESSONS.md`.
7. Subsequent runs load the promoted prompt version through [`core/evolution/prompt_loader.py`](../../core/evolution/prompt_loader.py).

## Operator Preference Rules

- Candidate prompt revisions include top-ranked entries from `memory/user_taste.json`.
- Direct operator feedback recorded after a run updates `memory/user_taste.json`.
- Explicit operator overrides take precedence over inferred preferences.

## Governance

- Changes to prompt templates and evolution scripts must satisfy [`AGENTS.md`](../../AGENTS.md) verification checks.
- Revisions to this protocol follow the same review and Git history requirements.
