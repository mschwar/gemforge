# GemForge Pipeline Stage Map

This guide maps how a `PipelineState` dictionary enters the orchestrator from `gemforge new` or `gemforge resume`, passes four state-transition gates, and outputs project files plus a terminal status envelope (`in_progress`, `success`, `partial`, or `blocked`). See [`README.md`](../../README.md) for CLI commands and [`AGENTS.md`](../../AGENTS.md) for state invariants.

## Ownership Map

- [`pipeline.py`](../../pipeline.py)
  - LangGraph graph assembly (`_build_pipeline`)
  - Node registration order and edge wiring
  - Node execution wrappers (`@logged_node`)
- [`core/pipeline_stages/failure_semantics.py`](../../core/pipeline_stages/failure_semantics.py)
  - Deploy outcome envelope (`live|local|failed`)
  - Git publish outcome envelope (`success|blocked`)
  - Routing decisions after review and publish
- [`core/pipeline_stages/context_builders.py`](../../core/pipeline_stages/context_builders.py)
  - Shared context block construction for parallel and operations stages
  - Specification file reads with deterministic fallbacks for missing files

## Critical State Gates

| Gate | Input Fields | Pass Transition | Fail Transition |
|---|---|---|---|
| Human Review | `approval_status` | `approved -> ruthless_interrogator` | `pending/rejected -> vision_polisher` |
| QA + Director | `tests_passed`, director verdict | `director_approved=True -> infra` | `director_approved=False -> human_review` |
| Deploy Outcome | `selected_platform`, deploy result | `pipeline_status` preserved (`success`) | web deploy failure -> `pipeline_status=partial` |
| Git Publish | `repo_path`, publish result | `git_published=True -> shipping` | `git_published=False -> END` and `pipeline_status=blocked` |

## Pipeline Status Model

- `in_progress`: run has started and remains active or paused at a gate.
- `success`: run completed and publish/deploy succeeded or native-local build output passed.
- `partial`: web deployment failed, while local project files and tests completed.
- `blocked`: a publish prerequisite failed and operator action is required.

## Operator-Facing Error Envelope

These fields travel in the final `PipelineState` dictionary on `blocked` or `partial` outcomes:

- `error_code`
- `error_stage`
- `operator_action`

CLI reporting in [`src/gemforge/cli.py`](../../src/gemforge/cli.py) reads these keys directly in `_print_final_report`.

## State Transition Sketch

```mermaid
flowchart LR
  review["human_review"] -->|approved| interrogator["ruthless_interrogator"]
  review -->|pending/rejected| polisher["vision_polisher"]
  qa["qa"] --> director["director"]
  director -->|approved| infra["infra/cicd/sre/deploy"]
  director -->|rejected| review
  deploy["deploy"] --> publish["git_publish"]
  publish -->|git_published=true| shipping["shipping -> weaver -> END"]
  publish -->|git_published=false| end["END (blocked)"]
```
