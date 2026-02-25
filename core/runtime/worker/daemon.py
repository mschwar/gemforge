"""
GemForge — Distributed Execution Fabric (Horizon 1 Prototype)
This module acts as the worker daemon. It listens to the EventBus
for `step.requested` events, executes the node logic locally,
and replies via the bus to resume the paused orchestrator graph.
"""
import json
import os
import threading
import time
from collections.abc import Callable

# We import the actual node functions to run them
import pipeline
from core.runtime.event_bus import event_bus
from core.runtime.logging import logger
from core.runtime.schema import StepEvent
from state import PipelineState


class DistributedWorker:
    def __init__(self, worker_id: str, supported_steps: list[str]):
        self.worker_id = worker_id
        self.supported_steps = supported_steps
        self._running = False
        self._heartbeat_thread: threading.Thread | None = None
        
        # In a real distributed system, this uses Redis PubSub or RabbitMQ.
        # Here we bind to the local in-memory bus for the prototype.
        event_bus.subscribe("step.requested", self._handle_request)

    def start(self):
        """Starts the worker daemon and heartbeat thread."""
        self._running = True
        logger.info(f"Worker [{self.worker_id}] started. Listening for: {self.supported_steps}")
        
        # Start heartbeat thread if Redis is enabled
        if hasattr(event_bus, 'redis'):
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._heartbeat_thread.start()

    def stop(self):
        """Stops the worker and heartbeat."""
        self._running = False
        logger.info(f"Worker [{self.worker_id}] stopped.")

    def _heartbeat_loop(self):
        """Periodically registers the worker in Redis to signal it is alive."""
        # Use a local reference to the worker_id to avoid threading issues
        worker_id = self.worker_id
        while self._running:
            redis_client = getattr(event_bus, 'redis', None)
            if redis_client:
                try:
                    # Register worker availability
                    worker_info = {
                        "worker_id": worker_id,
                        "supported_steps": self.supported_steps,
                        "last_seen": time.time()
                    }
                    redis_client.hset("gemforge:workers", worker_id, json.dumps(worker_info))
                    # Set an expiring key for the specific worker
                    redis_client.setex(f"gemforge:worker:{worker_id}:heartbeat", 30, "alive")
                except Exception:
                    # print(f"Heartbeat failed: {e}")
                    pass
            
            # Simple sleep that checks self._running frequently
            for _ in range(100):
                if not self._running:
                    return
                time.sleep(0.1)

    def _handle_request(self, event: StepEvent):
        """Callback when the orchestrator requests a node execution."""
        step_id = event.step_id
        
        if step_id not in self.supported_steps and "all" not in self.supported_steps:
            return # Not my job
            
        logger.info(f"Worker [{self.worker_id}] accepted task: {step_id} for run {event.run_id}")
        
        # 1. Extract the state slice from the orchestrator
        state_slice: dict = event.payload.get("state_slice", {})
        is_partial = event.payload.get("is_partial", False)
        
        if is_partial:
            # We need the full state for this run
            full_state = self._request_full_state(event.run_id, step_id)
            if not full_state:
                logger.error(f"Worker [{self.worker_id}] failed: Full state retrieval timed out for {event.run_id}")
                return
            state_slice = full_state

        # 2. Find the target function
        func_name = f"{step_id}_node"
        target_func: Callable = getattr(pipeline, func_name, None)
        
        if not target_func:
            logger.error(f"Worker [{self.worker_id}] failed: Unknown node '{func_name}'")
            return
            
        # 3. Execute the work
        if hasattr(target_func, "__wrapped__"):
            raw_func = target_func.__wrapped__
        else:
            raw_func = target_func

        try:
            start_time = time.time()
            # Execute the raw logic (this is where heavy compilation/tests happen)
            result_patch = raw_func(state_slice)
            duration = time.time() - start_time
            
            metrics = {
                "tokens_used": 0,
                "cost_usd": 0.0,
                "duration_sec": duration
            }
            
            logger.info(f"Worker [{self.worker_id}] completed task: {step_id}")
            
            # 4. Reply to the orchestrator to resume the graph
            self._reply_to_orchestrator(event.run_id, step_id, result_patch, metrics)
            
        except Exception as e:
            logger.error(f"Worker [{self.worker_id}] crashed on {step_id}: {e}")

    def _request_full_state(self, run_id: str, step_id: str) -> dict | None:
        """Requests and waits for the full state from the orchestrator."""
        response_received = threading.Event()
        full_state = None
        
        def on_state_delivered(data: dict):
            nonlocal full_state
            # We check the run_id from the event data (data is already unwrapped if using our new event_bus)
            if data.get("run_id") == run_id:
                full_state = data.get("payload", {}).get("full_state")
                response_received.set()

        # Subscribe to the response channel
        event_bus.subscribe("state.delivered", on_state_delivered)
        
        # Publish the request
        request_event = StepEvent(
            run_id=run_id,
            step_id=step_id,
            event_type="state.requested",
            payload={"worker_id": self.worker_id}
        )
        event_bus.publish(request_event)
        
        # Wait for reply with timeout
        success = response_received.wait(timeout=10)
        
        # Clean up temporary subscription
        event_bus.unsubscribe("state.delivered", on_state_delivered)
        
        return full_state

    def _reply_to_orchestrator(self, run_id: str, step_id: str, patch: dict, metrics: dict):
        """Publishes the result back so the dispatcher can un-pause LangGraph."""
        # The Dispatcher (in tools/runtime_dispatcher.py) listens for this.
        reply_event = StepEvent(
            run_id=run_id,
            step_id=step_id,
            event_type="worker.completed",
            payload={
                "state_patch": patch,
                "metrics": metrics
            }
        )
        event_bus.publish(reply_event)

# Factory for quick prototype booting
def boot_local_worker(name: str = "local-exec-1", steps: str = "all") -> DistributedWorker:
    worker = DistributedWorker(name, steps.split(","))
    worker.start()
    return worker

if __name__ == "__main__":
    import logging

    from core.runtime.logging import setup_logging
    setup_logging(logging.DEBUG)
    
    # Fake environment to tell pipeline.py NOT to proxy from within the worker
    os.environ["GEMFORGE_IS_WORKER"] = "true"
    
    worker_id = os.getenv("GEMFORGE_WORKER_ID", "docker-worker-1")
    enabled_steps = os.getenv("GEMFORGE_WORKER_ENABLED_STEPS", "all")
    
    worker = boot_local_worker(worker_id, enabled_steps)
    
    print(f"Worker {worker_id} running for steps: {enabled_steps}. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
