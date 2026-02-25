# GemForge — PERSISTENT.md
**Single Source of Truth & Immutable Governing Law**

**Last Updated:** 2026-02-24 19:55 MST

## Discipline Protocol v1.0 (Foundational Layer)

Every single step performed by any agent, any human operator, or any automated process in GemForge **MUST** follow this exact 8-step sequence without exception:

1. **Read** current PERSISTENT.md, progress.txt, and LESSONS.md (both factory AND active generated project).
2. **Perform** the work (with obsessive quality, taste, and strict scope discipline — only touch what you are allowed to touch).
3. **Update** documentation in the gemforge repo (progress.txt + LESSONS.md).
4. **Update** documentation in the generated project.
5. **Cross-check** consistency between PipelineState, files on disk, and git status.
6. **Git add/commit/push** the gemforge repo with message format:  
   `step N: [ShortName] - [clear one-line description]`
7. **Git add/commit/push** the generated project (same format).
8. **Log** to central audit trail and update PipelineState.

**This protocol is non-negotiable.** It is the unbreakable foundation that makes v2.0 (self-evolving agents + empire dashboard) possible.

**Scope Discipline Rule** (enforced by every agent):
- Each agent has explicit "WHAT YOU TOUCH" / "WHAT YOU NEVER TOUCH" rules in agents/*.md

## Current Phase
Phase 5 — Discipline Protocol (making foundations bulletproof)

## Overall Status
- Phases 1–4 complete (orchestration → CLI → Xcode → Vercel)
- All 7 major gaps closed
- Generated projects live in `../gemforge-projects/`
- Everything must remain clean, git-friendly, and professional.


## Active Modules (Phase 5)
- Module 2: Real QA / Testing Layer (Complete) — Automated test generation + execution + fail-safe human gate. Platform-aware (XCTest, Jest, pytest, etc.).


- Module 3: Version Control Module 3: Version Control & Collaboration (In Progress) Collaboration (Complete) — Auto GitHub repo + push + clean initial PR after successful build (gh CLI).


- Module 5: Cost Module 5: Cost & Rate-Limit Awareness (In Progress) Rate-Limit Awareness (Complete) — Real-time LLM token/cost tracking + final report.


- Module 6: Persistence & Multi-Gem Management (In Progress) — gems.db + gemforge list/status commands.

