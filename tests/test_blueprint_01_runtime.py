import unittest
import json
import sqlite3
import os
from pathlib import Path
from dataclasses import asdict

from core.runtime.schema import StepEvent
from core.runtime.outbox_store import OutboxStore
from core.runtime.event_bus import EventBus
from core.runtime.worker import Worker

class TestBlueprint01Runtime(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_checkpoints.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.outbox = OutboxStore(db_path=self.test_db)
        
    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_outbox_durability(self):
        """Verify events are saved to and retrieved from the outbox."""
        event = StepEvent(run_id="test-run", step_id="test-step", event_type="test.event")
        self.outbox.save_event(asdict(event))
        
        unpublished = self.outbox.get_unpublished_events()
        self.assertEqual(len(unpublished), 1)
        
        event_data = json.loads(unpublished[0]["event_json"])
        self.assertEqual(event_data["run_id"], "test-run")
        
        # Mark as published
        self.outbox.mark_as_published([unpublished[0]["id"]])
        self.assertEqual(len(self.outbox.get_unpublished_events()), 0)

    def test_worker_execution(self):
        """Verify the worker correctly executes a registered handler."""
        def mock_handler(state):
            return {"status": "worked", "received": state.get("input")}
            
        registry = {"mock_step": mock_handler}
        worker = Worker(step_registry=registry)
        
        event = StepEvent(
            run_id="run-123",
            step_id="mock_step",
            event_type="step.requested",
            payload={"state_slice": {"input": "hello"}}
        )
        
        result = worker.run_once(event)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["state_patch"]["received"], "hello")

    def test_event_bus_subscription(self):
        """Verify the EventBus notifies subscribers and the outbox."""
        bus = EventBus() # Note: uses global singleton outbox_store by default in implementation
        # For testing we'll just check if it calls our subscriber
        received = []
        bus.subscribe(lambda e: received.append(e))
        
        event = StepEvent(run_id="bus-run", step_id="bus-step", event_type="bus.test")
        bus.publish(event)
        
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["run_id"], "bus-run")

if __name__ == "__main__":
    unittest.main()
