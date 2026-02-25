"""
GemForge — Distributed Execution Fabric (Horizon 1 Prototype)
This module acts as the worker daemon. It listens to the EventBus
for `step.requested` events, executes the node logic locally,
and replies via the bus to resume the paused orchestrator graph.
"""
import os
import json
import time
from threading import Thread
from typing import Callable, Dict

from core.runtime.event_bus import event_bus
from core.runtime.schema import StepEvent
from core.runtime.logging import logger
from state import PipelineState

# We import the actual node functions to run them
import pipeline

class DistributedWorker:
    def __init__(self, worker_id: str, supported_steps: list[str]):
        self.worker_id = worker_id
        self.supported_steps = supported_steps
        self._running = False
        
        # In a real distributed system, this uses Redis PubSub or RabbitMQ.
        # Here we bind to the local in-memory bus for the prototype.
        event_bus.subscribe("step.requested", self._handle_request)

    def start(self):
        """Starts the worker daemon in a background thread."""
        self._running = True
        logger.info(f"Worker [{self.worker_id}] started. Listening for: {self.supported_steps}")
        # In a real system, this would be a blocking listen loop on Redis.

    def stop(self):
        self._running = False
        logger.info(f"Worker [{self.worker_id}] stopped.")

    def _handle_request(self, event: StepEvent):
        """Callback when the orchestrator requests a node execution."""
        step_id = event.step_id
        
        if step_id not in self.supported_steps and "all" not in self.supported_steps:
            return # Not my job
            
        logger.info(f"Worker [{self.worker_id}] accepted task: {step_id} for run {event.run_id}")
        
        # 1. Extract the state slice from the orchestrator
        state_slice: PipelineState = event.payload.get("state_slice", {})
        
        # 2. Find the target function
        func_name = f"{step_id}_node"
        target_func: Callable = getattr(pipeline, func_name, None)
        
        if not target_func:
            logger.error(f"Worker [{self.worker_id}] failed: Unknown node '{func_name}'")
            return
            
        # 3. Execute the work (Simulation of remote work)
        # We unwrap the @logged_node decorator if present to run the raw function
        if hasattr(target_func, "__wrapped__"):
            raw_func = target_func.__wrapped__
        else:
            raw_func = target_func

        try:
            start_time = time.time()
            # Execute the raw logic (this is where heavy compilation/tests happen)
            result_patch = raw_func(state_slice)
            duration = time.time() - start_time
            
            # Simulated usage (in a real worker, we'd track its local LLM calls)
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
            # Real implementation would send a failure message back

    def _reply_to_orchestrator(self, run_id: str, step_id: str, patch: Dict, metrics: Dict):
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
    
    worker = boot_local_worker("cli-worker", "qa,qa_generator")
    
    print("Worker running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()
