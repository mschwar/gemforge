# Horizon 3: Meta-Evolution Daemon

**Status**: Prototype Phase  

The incident daemon accepts `POST /webhook/incident` JSON alerts containing a target project path, platform name, and production stack trace. It runs the bounded repair loop and local test suite against that checkout, then opens a GitHub pull request when verification passes.

## Architecture
- **Webhook Receiver ([`core/runtime/singularity_daemon.py`](../../../core/runtime/singularity_daemon.py))**: An HTTP endpoint for external Application Performance Monitoring (APM) systems such as Sentry or Datadog that accepts structured incident payloads.
- **Incident Dispatcher**: Builds a synthetic `PipelineState` populated with `repo_path`, `selected_platform`, and the incoming stack trace as `test_report`, then invokes `repair_node`.
- **Automated Pull Request Stage**: Routes the state to `git_publish_node` to push a fix branch and open a pull request only when `repair_node` returns `tests_passed=True`.
- **Prompt Feedback Loop (Planned)**: Aggregates recurring production incident signatures into candidate prompt updates under [`docs/v2.0/EVOLUTION_DISCIPLINE_PROTOCOL.md`](../../v2.0/EVOLUTION_DISCIPLINE_PROTOCOL.md).

## Prototype Notes
- [`core/runtime/singularity_daemon.py`](../../../core/runtime/singularity_daemon.py) uses Python's standard-library `http.server` so local incident testing requires zero extra web-framework dependencies.
- Unverified patches never reach `git_publish_node`; failed repairs stop locally and log the diagnostic report.

## How to Test the Prototype
1. Start the daemon locally:
   ```bash
   python -m core.runtime.singularity_daemon
   ```
2. In a second terminal, send a simulated APM incident payload with `curl`:
   ```bash
   curl -X POST http://localhost:8080/webhook/incident \
     -H "Content-Type: application/json" \
     -d '{
           "project_path": "/path/to/target-project",
           "platform": "web",
           "incident_title": "TypeError: Cannot read properties of undefined (reading map)",
           "stack_trace": "TypeError: Cannot read properties of undefined (reading map)\n    at UserList (src/components/UserList.tsx:15:23)"
         }'
   ```
3. Inspect the daemon output to confirm signature extraction, patch generation, test execution, and gated Git publish behavior.
