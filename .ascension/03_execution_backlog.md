# Execution Backlog: Horizon 1 — Distributed Execution Fabric

**Target Objective:** Swapping the prototype's in-memory `event_bus` with a robust message broker (Redis PubSub) and containerizing `daemon.py` for isolated execution.

---

## [ ] Step 1: Redis Event Bus Implementation
*   **Gate 1: Tests:**
    *   Create `tests/test_event_bus_redis.py`: Integration test requiring a local Redis instance (mocked or real) to verify cross-process pub/sub.
*   **Gate 2: Implementation:**
    *   `core/runtime/event_bus.py`: Implement `RedisEventBus` class using `redis-py`.
    *   `.env.example`: Add `REDIS_URL` and `USE_REDIS` flag.
*   **Gate 3: Validation:**
    *   `pytest tests/test_event_bus_redis.py`
    *   `ruff check core/runtime/event_bus.py`
*   **Gate 4: Fallback:**
    *   `USE_REDIS=false` defaults to the legacy `InMemoryEventBus`.

## [ ] Step 2: Distributed State & Heartbeat Synchronization
*   **Gate 1: Tests:**
    *   Create `tests/test_worker_sync.py`: Verify that a worker can retrieve the full `PipelineState` and return a patch that correctly merges into the orchestrator's graph.
*   **Gate 2: Implementation:**
    *   `core/runtime/worker/daemon.py`: Refactor `_handle_request` to support full state retrieval if `state_slice` is partial.
    *   `core/runtime/worker/dispatcher.py`: Implement worker heartbeat monitoring via Redis to detect "Ghost Workers."
*   **Gate 3: Validation:**
    *   `pytest tests/test_worker_sync.py`
    *   `ruff check core/runtime/worker/`
*   **Gate 4: Fallback:**
    *   Worker continues to accept `state_slice` if full state retrieval is unavailable.

## [ ] Step 3: Containerization (Dockerfile & Compose)
*   **Gate 1: Tests:**
    *   `tests/test_worker_container.py`: Smoke test ensuring the worker daemon starts inside a container and connects to a linked Redis service.
*   **Gate 2: Implementation:**
    *   `Dockerfile.worker`: Build an image with `gemforge` dependencies + `npm`/`xcodegen`.
    *   `docker-compose.yml`: Define `redis`, `worker`, and `orchestrator` (optional) services.
*   **Gate 4: Fallback:**
    *   `daemon.py` remains runnable locally via `python -m core.runtime.worker.daemon`.

## [ ] Step 4: Orchestrator Resilience & Timeouts
*   **Gate 1: Tests:**
    *   `tests/test_worker_timeout.py`: Mock a slow/missing worker and verify the orchestrator raises a `TimeoutError` or transitions to a `blocked` state.
*   **Gate 2: Implementation:**
    *   `pipeline.py` (`logged_node` decorator): Add a `timeout` parameter to the `interrupt()` payload.
    *   `core/runtime/worker/dispatcher.py`: Add task tracking to reap expired requests.
*   **Gate 3: Validation:**
    *   `pytest tests/test_worker_timeout.py`
*   **Gate 4: Fallback:**
    *   Default timeout is set to `None` (unbounded) to match legacy behavior unless configured.

---
**Status:** Ingested Horizon 1 blueprints. Pipeline backlog generated with strict execution gates.
