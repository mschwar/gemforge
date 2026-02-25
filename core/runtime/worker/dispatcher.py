"""
GemForge — Distributed Dispatcher (Horizon 1 Prototype)
This module acts as the "Controller" for the orchestrator.
When a node yields an `interrupt`, LangGraph pauses. This service
listens for the worker's reply and injects the `Command(resume=...)`
to restart the graph exactly where it left off.
"""
import json
import os
import time
from threading import Thread

from langgraph.types import Command

from core.runtime.event_bus import event_bus
from core.runtime.logging import logger
from core.runtime.schema import StepEvent


class OrchestratorDispatcher:
    def __init__(self, pipeline_app):
        self.app = pipeline_app
        self._running = False
        self._active_requests: dict[str, dict] = {} # run_id -> request_info
        self._monitor_thread: Thread | None = None
        
        # Subscribe to worker completions
        event_bus.subscribe("worker.completed", self._handle_worker_reply)
        event_bus.subscribe("worker.failed", self._handle_worker_failure)
        # We also listen to requests to track timeouts
        event_bus.subscribe("step.requested", self._track_request)
        # Handle state requests from workers
        event_bus.subscribe("state.requested", self._handle_state_request)

    def start(self):
        self._running = True
        logger.info("Dispatcher started. Listening for worker completions.")
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._running = False
        logger.info("Dispatcher stopped.")

    def _track_request(self, event: StepEvent | dict):
        """Keep track of sent requests to monitor for timeouts."""
        if isinstance(event, dict):
            run_id = event.get("run_id")
            step_id = event.get("step_id")
        else:
            run_id = event.run_id
            step_id = event.step_id

        timeout_sec = int(os.getenv("GEMFORGE_WORKER_TIMEOUT", "300"))
        self._active_requests[run_id] = {
            "step_id": step_id,
            "timeout_at": time.time() + timeout_sec
        }

    def _monitor_loop(self):
        """Periodic check for timed-out worker tasks and stale workers."""
        while self._running:
            now = time.time()
            expired_runs = []
            
            for run_id, info in self._active_requests.items():
                if now > info["timeout_at"]:
                    expired_runs.append((run_id, info["step_id"]))
            
            for run_id, step_id in expired_runs:
                logger.warning(f"Task {step_id} (Run: {run_id}) timed out.")
                self._handle_timeout(run_id, step_id)
                if run_id in self._active_requests:
                    del self._active_requests[run_id]
            
            # Prune ghost workers
            try:
                self.get_active_workers()
            except Exception:
                pass
            
            time.sleep(5)

    def _handle_state_request(self, event: StepEvent | dict):
        """Worker requested full state. Retrieve from LangGraph and publish back."""
        # Normalize event (it might be a dict if from Redis)
        if isinstance(event, dict):
            run_id = event.get("run_id")
            step_id = event.get("step_id")
        else:
            run_id = event.run_id
            step_id = event.step_id

        if not run_id:
            return

        logger.info(f"Dispatcher delivering full state for run {run_id}...")
        config = {"configurable": {"thread_id": run_id}}
        
        try:
            snapshot = self.app.get_state(config)
            full_state = snapshot.values
            
            # Publish back
            reply = StepEvent(
                run_id=run_id,
                step_id=step_id,
                event_type="state.delivered",
                payload={"full_state": full_state}
            )
            event_bus.publish(reply)
        except Exception as e:
            logger.error(f"Dispatcher failed to deliver state for {run_id}: {e}")

    def _handle_timeout(self, run_id: str, step_id: str):
        """Injects a failure state back into the graph on timeout."""
        config = {"configurable": {"thread_id": run_id}}
        resume_payload = {
            "status": "failed",
            "error": f"Worker timeout after {os.getenv('GEMFORGE_WORKER_TIMEOUT', '300')}s"
        }
        try:
            self.app.invoke(Command(resume=resume_payload), config)
        except Exception as e:
            logger.error(f"Failed to resume graph after timeout: {e}")

    def get_active_workers(self) -> list[dict]:
        """Queries Redis for workers with an active heartbeat."""
        redis_client = getattr(event_bus, 'redis', None)
        if not redis_client:
            return []
            
        workers = []
        try:
            all_workers = redis_client.hgetall("gemforge:workers")
            for worker_id_bytes, info_json in all_workers.items():
                worker_id = worker_id_bytes.decode('utf-8')
                # Check if heartbeat key still exists
                if redis_client.exists(f"gemforge:worker:{worker_id}:heartbeat"):
                    workers.append(json.loads(info_json))
                else:
                    # Clean up stale worker registration
                    redis_client.hdel("gemforge:workers", worker_id)
        except Exception as e:
            logger.error(f"Failed to query active workers: {e}")
            
        return workers

    def _handle_worker_reply(self, event: StepEvent | dict):
        """Callback when a distributed worker finishes a node task."""
        # Normalize event
        if isinstance(event, dict):
            run_id = event.get("run_id")
            step_id = event.get("step_id")
            payload = event.get("payload", {})
        else:
            run_id = event.run_id
            step_id = event.step_id
            payload = event.payload

        # Remove from active tracking
        if run_id in self._active_requests:
            del self._active_requests[run_id]
            
        logger.info(f"Dispatcher received completion for {step_id} (Run: {run_id})")
        
        # We need the thread_id to resume the correct graph instance.
        thread_id = run_id 
        
        # Build the LangGraph config to target the paused state
        config = {"configurable": {"thread_id": thread_id}}
        
        # The data to inject back into the graph
        patch: dict = payload.get("state_patch", {})
        metrics: dict = payload.get("metrics", {})
        
        # Create the resume command. The `logged_node` decorator expects this structure.
        resume_payload = {
            "state_patch": patch,
            "metrics": metrics
        }
        
        try:
            logger.info(f"Dispatcher resuming graph for {thread_id} at node {step_id}...")
            # This is the magic: we inject the worker's result back into the graph.
            # The graph wakes up, the `interrupt()` returns this dict, and the node completes.
            self.app.invoke(Command(resume=resume_payload), config)
        except Exception as e:
            logger.error(f"Dispatcher failed to resume graph: {e}")

    def _handle_worker_failure(self, event: StepEvent | dict):
        """Handles when a worker crashes."""
        if isinstance(event, dict):
            step_id = event.get("step_id")
            error = event.get("payload", {}).get("error")
        else:
            step_id = event.step_id
            error = event.payload.get("error")
            
        logger.error(f"Dispatcher received failure for {step_id}: {error}")

def boot_dispatcher(pipeline_app) -> OrchestratorDispatcher:
    dispatcher = OrchestratorDispatcher(pipeline_app)
    dispatcher.start()
    return dispatcher
