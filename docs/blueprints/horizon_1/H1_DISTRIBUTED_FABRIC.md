# Horizon 1: Distributed Execution Fabric

**Status**: Prototype Phase  

When `GEMFORGE_WORKER_ENABLED=true`, the orchestrator emits `step.requested` events instead of running blocking subprocesses (`npm test`, `xcodebuild`, `git`) inline. Separate worker processes execute those stages, emit `worker.completed` events, and hand state patches plus usage metrics back to the background dispatcher.

## Architecture
- **Orchestrator ([`pipeline.py`](../../../pipeline.py))**: The `logged_node` decorator checks `GEMFORGE_WORKER_ENABLED` and `GEMFORGE_WORKER_ENABLED_STEPS`. For delegated steps, it pauses the LangGraph thread with `interrupt({"action": "wait_for_worker"})` and publishes a `step.requested` event.
- **Worker ([`core/runtime/worker/daemon.py`](../../../core/runtime/worker/daemon.py))**: A separate worker process subscribes to the event bus, claims `step.requested` jobs, runs the target stage locally or inside a container, and publishes `worker.completed` with the `PipelineState` patch and cost metrics.
- **Dispatcher ([`core/runtime/worker/dispatcher.py`](../../../core/runtime/worker/dispatcher.py))**: A background listener receives `worker.completed` events and resumes the suspended LangGraph thread with `Command(resume={"state_patch": patch, "metrics": metrics})` so the orchestrator never blocks on long subprocess input/output.

## Prototype Notes
- Local single-host runs use the SQLite/in-memory [`core/runtime/event_bus.py`](../../../core/runtime/event_bus.py) transport, while multi-host deployments use the Redis adapter tested in [`tests/test_event_bus_redis.py`](../../../tests/test_event_bus_redis.py).
- The `logged_node` wrapper in [`pipeline.py`](../../../pipeline.py) toggles per-step worker delegation via `should_proxy`, preserving direct in-process execution when worker mode is disabled.

## How to Test the Prototype
1. Start a worker daemon in Terminal A:
   ```bash
   export GEMFORGE_WORKER_ENABLED=true
   export GEMFORGE_IS_WORKER=true
   export GEMFORGE_WORKER_ENABLED_STEPS=qa,qa_generator
   python -m core.runtime.worker.daemon
   ```
2. Launch a pipeline run in Terminal B:
   ```bash
   export GEMFORGE_WORKER_ENABLED=true
   gemforge new "A simple counter app"
   ```
