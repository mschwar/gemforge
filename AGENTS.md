# AGENTS.md

GemForge is a staged Python pipeline that turns a plain-text product idea (plus optional context files) into specifications, template-scaffolded application code, test results, and release manifests.

## Reading Order

Read these files before modifying orchestration, prompts, or state schemas:

1. [`AGENTS.md`](AGENTS.md)
2. [`README.md`](README.md)
3. [`PERSISTENT.md`](PERSISTENT.md)
4. [`state.py`](state.py)
5. [`pipeline.py`](pipeline.py)
6. [`docs/architecture/PIPELINE_STAGE_MAP.md`](docs/architecture/PIPELINE_STAGE_MAP.md)

## Architecture Invariants

- Keep `PipelineState` in [`state.py`](state.py) backward-compatible with CLI reporting in [`src/gemforge/cli.py`](src/gemforge/cli.py), including `pipeline_status`, `error_code`, `error_stage`, and `operator_action`.
- Preserve node dependency declarations in [`core/build/graph.py`](core/build/graph.py) whenever nodes are added, renamed, or rewired in [`pipeline.py`](pipeline.py).
- Keep generated project writes confined to `PROJECTS_ROOT` and never overwrite `.env` or credential files.
- Keep prompt changes traceable under `agents/prompts/` in accordance with [`docs/v2.0/EVOLUTION_DISCIPLINE_PROTOCOL.md`](docs/v2.0/EVOLUTION_DISCIPLINE_PROTOCOL.md).

## Verification

- Run the zero-dependency documentation hygiene gate with system Python:
  ```bash
  /usr/bin/python3 -m unittest tests/test_doc_hygiene.py -v
  ```
- Run targeted or full Python tests when modifying runtime, build-graph, memory, or pipeline modules:
  ```bash
  pytest -q
  ```
- Do not add hosted cloud-VM GitHub Actions `pull_request:` or `push:` triggers.

## Documentation Hygiene

- Lead human-facing documentation ([`README.md`](README.md), [`docs/architecture/PIPELINE_STAGE_MAP.md`](docs/architecture/PIPELINE_STAGE_MAP.md), [`docs/blueprints/`](docs/blueprints/BLUEPRINT_01_EVENT_DRIVEN_FORGE_RUNTIME.md), and [`docs/v2.0/EVOLUTION_DISCIPLINE_PROTOCOL.md`](docs/v2.0/EVOLUTION_DISCIPLINE_PROTOCOL.md)) with concrete inputs, checks or processing steps, and outputs before introducing internal node names.
- Keep [`README.md`](README.md) encoded as plain UTF-8 without a byte order mark (BOM) and open it with a `## TL;DR` section of `1..60` words.
- Keep every prose sentence in scoped human-facing guides at or under 45 words.
- Expand unfamiliar uppercase acronyms at first use as `Full Term (ACRONYM)` without backticks inside parentheses, and avoid banned AI filler or ambiguous modals.
- Use valid repository-relative Markdown links and `#heading` anchors, with zero machine-local file URIs.
- Leave dated historical audit logs (`docs/audits/2026-02-25_*`, `docs/roadmaps/2026-02-25-*`, and `LESSONS.md`) untouched when updating active guides.
