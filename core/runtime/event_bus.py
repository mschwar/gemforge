import json
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional

from .outbox_store import outbox_store
from .schema import StepEvent
from .event_logger import event_logger, StepEvent as SchemaStepEvent

class EventBus:
    """The central event bus for GemForge.
    
    Supports:
    - Durable publishing to the outbox (SQLite).
    - In-process subscriptions for local dispatch.
    - Automatic persistent logging of all events.
    """
    def __init__(self):
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        # Automatically subscribe the logger for global run tracking
        self.subscribe(self._log_callback)

    def _log_callback(self, event_dict: Dict[str, Any]):
        # Re-construct event for the logger
        event = SchemaStepEvent(
            run_id=event_dict["run_id"],
            step_id=event_dict["step_id"],
            event_type=event_dict["event_type"],
            payload=event_dict["payload"],
            event_id=event_dict["event_id"],
            created_at=event_dict["created_at"],
            attempt=event_dict["attempt"]
        )
        event_logger.log_event(event)

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for every event published on this bus instance."""
        self._subscribers.append(callback)

    def publish(self, event: StepEvent):
        """Publish an event to the outbox and notify in-process subscribers."""
        event_dict = asdict(event)
        
        # 1. Persist to outbox for durability and async dispatch
        outbox_store.save_event(event_dict)
        
        # 2. Notify in-process subscribers (for real-time logging/CLI tail)
        for sub in self._subscribers:
            try:
                sub(event_dict)
            except Exception as e:
                # We don't want subscriber failure to block the main thread
                print(f"   ⚠️ EventBus subscriber error: {e}")

# Global singleton
event_bus = EventBus()
