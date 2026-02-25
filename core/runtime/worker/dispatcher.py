"""
GemForge — Distributed Dispatcher (Horizon 1 Prototype)
This module acts as the "Controller" for the orchestrator.
When a node yields an `interrupt`, LangGraph pauses. This service
listens for the worker's reply and injects the `Command(resume=...)`
to restart the graph exactly where it left off.
"""
import os
import time
from threading import Thread
from typing import Dict

from core.runtime.event_bus import event_bus
from core.runtime.schema import StepEvent
from core.runtime.logging import logger
from langgraph.types import Command

class OrchestratorDispatcher:
    def __init__(self, pipeline_app):
        self.app = pipeline_app
        self._running = False
        
        # Subscribe to worker completions
        event_bus.subscribe("worker.completed", self._handle_worker_reply)
        event_bus.subscribe("worker.failed", self._handle_worker_failure)

    def start(self):
        self._running = True
        logger.info("Dispatcher started. Listening for worker completions.")

    def stop(self):
        self._running = False
        logger.info("Dispatcher stopped.")

    def _handle_worker_reply(self, event: StepEvent):
        """Callback when a distributed worker finishes a node task."""
        run_id = event.run_id
        step_id = event.step_id
        
        logger.info(f"Dispatcher received completion for {step_id} (Run: {run_id})")
        
        # We need the thread_id to resume the correct graph instance.
        # In GemForge, run_id is essentially the thread_id.
        thread_id = run_id 
        
        # Build the LangGraph config to target the paused state
        config = {"configurable": {"thread_id": thread_id}}
        
        # The data to inject back into the graph
        patch: Dict = event.payload.get("state_patch", {})
        metrics: Dict = event.payload.get("metrics", {})
        
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

    def _handle_worker_failure(self, event: StepEvent):
        """Handles when a worker crashes."""
        # For simplicity in the prototype, we just log.
        # A robust system would inject an error state back into the graph.
        logger.error(f"Dispatcher received failure for {event.step_id}: {event.payload.get('error')}")

def boot_dispatcher(pipeline_app) -> OrchestratorDispatcher:
    dispatcher = OrchestratorDispatcher(pipeline_app)
    dispatcher.start()
    return dispatcher
