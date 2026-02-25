# GemForge v2.0 – Evolution Discipline Protocol
**Version**: 1.0  
**Date**: 2026-02-24  
**Purpose**: Guarantee that self-evolution is safe, aligned, traceable, and never breaks the rock-solid foundations.

## The Three Laws of Evolution
1. **Endure** – Never degrade performance. Every prompt change must pass validation on past gems.
2. **Excel** – Improvements must be measurable (quality, alignment, speed, user delight).
3. **Evolve** – Every gem triggers lesson capture. Prompt history lives forever in git.

## Core Components
- **User Taste Memory** – Your values, style, tech preferences, “never do X” rules.
- **Lessons Database** – SQLite (`lessons/lessons.db`) + human-readable summaries in LESSONS.md.
- **Versioned Prompts** – `agents/prompts/{agent}/v{version}.md` + `metadata.json`.
- **Weaver Reflection Subgraph** – Dedicated LangGraph that runs post-gem.

## Workflow (automated + human gate)
1. Gem finishes → Weaver Reflection Subgraph runs.
2. Lessons extracted → stored in DB + appended to LESSONS.md → git commit.
3. When enough high-impact lessons exist (or manual `forge evolve`) → Evolver proposes new prompt versions.
4. Proposal generated as `evolutions/proposal_YYYYMMDD.md` with full diff + rationale.
5. **Human approval required**: `forge approve-evolution --id XXX` (reviews diff, runs shadow test if chosen).
6. Approved → prompts updated, git commit with full explanation, LESSONS.md updated, push.
7. Factory now uses improved agents for next gem.

## Symbiosis Rules (Pillar 8)
- Every evolution prompt always includes top-k excerpts from your taste memory.
- After any interaction you can say “Log feedback: …” → instantly added to memory.
- Overrides from you have highest weight.

## Git & Documentation
- Every change follows existing Discipline Protocol.
- This file itself evolves via the same process.

This protocol is the operating system of the Dark Factory. It will be versioned and improved with every cycle.
