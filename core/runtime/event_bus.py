import json
import os
import threading
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

import redis

from .event_logger import StepEvent as SchemaStepEvent
from .event_logger import event_logger
from .outbox_store import outbox_store
from .schema import StepEvent


class EventBus:
    """The central event bus for GemForge (In-Memory)."""
    def __init__(self):
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []
        # Automatically subscribe the logger for global run tracking
        self.subscribe("*", self._log_callback)

    def _log_callback(self, event_dict: dict[str, Any]):
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

    def subscribe(self, topic: str, callback: Callable[[dict[str, Any]], None]):
        """Register a callback for every event published on this bus instance.
        
        Note: The 'topic' (step_id) is currently ignored by the base InMemory bus
        which broadcasts all events to all subscribers.
        """
        self._subscribers.append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[dict[str, Any]], None]):
        """Unregister a callback from the bus."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

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

class RedisEventBus(EventBus):
    """Distributed Event Bus using Redis PubSub."""
    def __init__(self, redis_url: str | None = None, redis_client: Any | None = None):
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = redis.from_url(redis_url or "redis://localhost:6379")
        
        self.pubsub = self.redis.pubsub()
        self._topic_callbacks: dict[str, list[Callable]] = {}
        self._listen_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        
        super().__init__()

    def subscribe(self, topic: str, callback: Callable[[dict[str, Any]], None]):
        """Subscribe to a specific topic (step_id) via Redis PubSub."""
        # Ensure background listener is running
        if not self._listen_thread:
            # We always psubscribe to everything because the logger (base class) needs it,
            # and it simplifies routing and avoids duplicates from overlapping subscriptions.
            self.pubsub.psubscribe(**{"*": self._redis_message_handler})
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()

        if topic == "*":
            super().subscribe(topic, callback)
        else:
            if topic not in self._topic_callbacks:
                self._topic_callbacks[topic] = []
            self._topic_callbacks[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[dict[str, Any]], None]):
        """Unregister a callback from the bus."""
        if topic == "*":
            super().unsubscribe(topic, callback)
        else:
            if topic in self._topic_callbacks and callback in self._topic_callbacks[topic]:
                self._topic_callbacks[topic].remove(callback)
                # If no more subscribers for this topic, we could technically unsubscribe from Redis,
                # but we're using psubscribe("*") anyway, so there's no need.

    def publish(self, event: StepEvent):
        """Publish an event to Redis and the local outbox."""
        event_dict = asdict(event)
        
        # 1. Local outbox durability
        outbox_store.save_event(event_dict)
        
        # 2. Redis Publish (Broadcast to other processes)
        # We add a sender ID to avoid processing our own messages twice
        message_data = {
            "sender_id": id(self),
            "event": event_dict
        }
        json_payload = json.dumps(message_data)
        
        # Publish to both the specific step channel and the global event_type channel
        # This ensures subscribers listening for either receive the message.
        self.redis.publish(event.step_id, json_payload)
        if event.event_type != event.step_id:
            self.redis.publish(event.event_type, json_payload)
        
        # 3. Notify local subscribers (immediate feedback)
        # Notify specific topic subscribers (by step_id)
        if event.step_id in self._topic_callbacks:
            for sub in self._topic_callbacks[event.step_id]:
                try:
                    sub(event_dict)
                except Exception as e:
                    print(f"   ⚠️ EventBus topic subscriber error: {e}")

        # Notify specific topic subscribers (by event_type)
        if event.event_type != event.step_id and event.event_type in self._topic_callbacks:
            for sub in self._topic_callbacks[event.event_type]:
                try:
                    sub(event_dict)
                except Exception as e:
                    print(f"   ⚠️ EventBus event_type subscriber error: {e}")

        # Notify global subscribers
        for sub in self._subscribers:
            try:
                sub(event_dict)
            except Exception as e:
                print(f"   ⚠️ EventBus global subscriber error: {e}")

    def _redis_message_handler(self, message: dict):
        """Handles raw messages from Redis and routes to local callbacks."""
        # Only process 'pmessage' to avoid duplicates if someone also used 'subscribe'
        if message['type'] == 'pmessage':
            try:
                data_wrapper = json.loads(message['data'])
                # Compatibility check for messages without sender_id
                if isinstance(data_wrapper, dict) and "sender_id" in data_wrapper:
                    if data_wrapper["sender_id"] == id(self):
                        return # Ignore our own messages
                    data = data_wrapper["event"]
                else:
                    data = data_wrapper
                
                channel = message['channel'].decode('utf-8') if isinstance(message['channel'], bytes) else message['channel']
                
                # Notify specific topic subscribers
                if channel in self._topic_callbacks:
                    for callback in self._topic_callbacks[channel]:
                        try:
                            callback(data)
                        except Exception as e:
                            print(f"   ⚠️ RedisEventBus topic callback error: {e}")
                
                # Notify global subscribers
                for sub in self._subscribers:
                    try:
                        sub(data)
                    except Exception as e:
                        # Log error but continue to next subscriber
                        print(f"   ⚠️ RedisEventBus global subscriber error: {e}")
                    
            except Exception as e:
                print(f"   ⚠️ RedisEventBus handler error: {e}")

    def _listen_loop(self):
        """Background thread to process Redis PubSub messages."""
        while not self._stop_event.is_set():
            try:
                # Use a timeout to allow checking the stop_event
                self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except Exception:
                # print(f"Redis listen error: {e}")
                pass

def get_event_bus() -> EventBus:
    """Factory to get the configured event bus singleton."""
    use_redis = os.getenv("USE_REDIS", "false").lower() == "true"
    if use_redis:
        return RedisEventBus(redis_url=os.getenv("REDIS_URL"))
    return EventBus()

# Global singleton
event_bus = get_event_bus()
