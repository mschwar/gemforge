# GemForge Pipeline Stage Map (Phase 5)

This document is the fast path for humans and AI coding assistants to understand
which module owns each orchestration concern and how state transitions gate the run.

## Ownership Map

- `pipeline.py`
  - LangGraph graph assembly (`_build_pipeline`)
  - Node registration order and edge wiring
  - Node execution wrappers (`@logged_node`)
- `core/pipeline_stages/failure_semantics.py`
  - Deploy outcome envelope (`live|local|failed`)
  - Git publish outcome envelope (`success|blocked`)
  - Routing decisions after review and publish
- `core/pipeline_stages/context_builders.py`
  - Shared context block construction for parallel and ops stages
  - Spec file reads with stable fallbacks for missing docs

## Critical State Gates

| Gate | Input Fields | Pass Transition | Fail Transition |
|---|---|---|---|
| Human Review | `approval_status` | `approved -> ruthless_interrogator` | `pending/rejected -> vision_polisher` |
| QA + Director | `tests_passed`, director verdict | `director_approved=True -> infra` | `director_approved=False -> human_review` |
| Deploy Outcome | `selected_platform`, deploy result | `pipeline_status` preserved (`success`) | web deploy failure -> `pipeline_status=partial` |
| Git Publish | `repo_path`, publish result | `git_published=True -> shipping` | `git_published=False -> END` and `pipeline_status=blocked` |

## Pipeline Status Model

- `in_progress`: run has started but not finalized.
- `success`: fully completed and publish/deploy succeeded or native-local deploy accepted.
- `partial`: deploy failed for non-native targets, but run produced usable local artifacts.
- `blocked`: critical publish prerequisite failed and operator action is required.

## Operator-Facing Error Envelope

These fields must travel in final state on blocked/partial outcomes:

- `error_code`
- `error_stage`
- `operator_action`

CLI reporting consumes these keys directly in `_print_final_report` and must remain compatible.

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
