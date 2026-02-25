# Horizon 3: The Meta-Evolution Daemon (Singularity Seed)

**Status**: Prototype Phase
**Impact**: 1000x Autonomous Evolution & Self-Healing

## The Leap
GemForge stops being merely a "generation pipeline" that exits upon completion. Instead, it becomes a continuous, living daemon that sits alongside the deployed application. It ingests production telemetry and error logs (from systems like Datadog or Sentry) via webhooks. When an anomaly is detected, it autonomously triggers the `agentic_loop.py` to reproduce the error, write a patch, and open a Pull Request on GitHub—all without human intervention.

## Architecture
- **Webhook Receiver (`core/runtime/singularity_daemon.py`)**: A lightweight HTTP endpoint (e.g., FastAPI) exposed to external APM tools. It listens for `production.incident` webhooks containing stack traces and context.
- **Incident Dispatcher**: The daemon clones/pulls the latest `main` branch of the target project, constructs a synthetic `PipelineState` containing the production stack trace as the `test_report`, and directly invokes the `repair_node`.
- **Auto-PR Engine**: If the `repair_node` returns `tests_passed=True` (meaning it successfully compiled/tested the fix locally), the daemon routes the state to the `git_publish_node` to open a Pull Request.
- **Meta-Weaver (Future)**: A specialized background agent that periodically reviews the daemon's success rate and writes PRs against GemForge's *own* repository to improve prompt logic.

## Implementation Details (Prototype)
- The prototype is implemented as a simple HTTP service using Python's built-in `http.server` (for zero dependency setup) or easily adaptable to FastAPI for production.
- It receives a JSON payload mimicking a Sentry alert, translates it into a GemForge state, and initiates the repair sequence.

## How to Test the Prototype
1. Start the daemon locally:
   ```bash
   python -m core.runtime.singularity_daemon
   ```
2. In a separate terminal, simulate a production APM alert via `curl`:
   ```bash
   curl -X POST http://localhost:8080/webhook/incident 
        -H "Content-Type: application/json" 
        -d '{
              "project_path": "/Users/mschwar/Documents/GitHub/gemforge/my-broken-app",
              "platform": "web",
              "incident_title": "TypeError: Cannot read properties of undefined (reading '''map'')",
              "stack_trace": "TypeError: Cannot read properties of undefined (reading '''map'')
    at UserList (src/components/UserList.tsx:15:23)
    at renderWithHooks (node_modules/react-dom/cjs/react-dom.development.js:15486:18)"
            }'
   ```
3. Watch the daemon autonomously diagnose the error, apply a patch, verify it, and (if configured with a real GitHub token and repo) open a PR to fix the broken application.
