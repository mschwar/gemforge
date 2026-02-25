# Horizon 1: Distributed Execution Fabric

**Status**: Prototype Phase
**Impact**: 10x Operational Reliability & Latency Reduction

## The Leap
Decouple all heavy shell commands (`npm test`, `xcodebuild`, `git`) from the central LangGraph orchestrator into isolated, ephemeral worker processes.

## Architecture
- **Orchestrator (`pipeline.py`)**: Uses the `logged_node` decorator to trap execution. If `GEMFORGE_WORKER_ENABLED=true`, the node suspends the LangGraph state using `interrupt({"action": "wait_for_worker"})` and emits a `step.requested` event.
- **Worker (`core/runtime/worker/daemon.py`)**: A distributed process listening to the `EventBus`. It claims `step.requested` events, executes the heavy lifting locally (or inside a Docker container/Firecracker microVM), and emits a `worker.completed` event containing the mutated `PipelineState` dict and usage metrics.
- **Dispatcher (`core/runtime/worker/dispatcher.py`)**: A background thread running alongside the Orchestrator. It listens for `worker.completed` events and invokes the paused LangGraph thread with `Command(resume={"state_patch": patch, "metrics": metrics})`, allowing the orchestrator to continue instantly without ever blocking on IO.

## Implementation Details (Prototype)
- The prototype currently utilizes the existing synchronous/in-memory `event_bus.py`.
- To achieve true distributed execution, the `event_bus` must be swapped with a Redis PubSub or RabbitMQ adapter.
- The `logged_node` decorator in `pipeline.py` natively supports this "Strangler Fig" pattern via the `should_proxy` boolean.

## How to Test the Prototype
1. Open Terminal A (Worker):
   ```bash
   export GEMFORGE_WORKER_ENABLED=true
   export GEMFORGE_IS_WORKER=true
   export GEMFORGE_WORKER_ENABLED_STEPS=qa,qa_generator
   python -m core.runtime.worker.daemon
   ```
2. Open Terminal B (Orchestrator):
   ```bash
   export GEMFORGE_WORKER_ENABLED=true
   gemforge new "A simple counter app"
   ```
