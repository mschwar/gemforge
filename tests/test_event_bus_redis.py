import os
import json
import pytest
import fakeredis
import uuid
from unittest.mock import patch, MagicMock
from core.runtime.event_bus import RedisEventBus, StepEvent

@pytest.fixture
def mock_redis():
    """Provides a fake redis client for testing."""
    return fakeredis.FakeRedis()

def test_redis_event_bus_publish(mock_redis):
    """Verify that publishing to RedisEventBus calls redis.publish with JSON."""
    bus = RedisEventBus(redis_client=mock_redis)
    event = StepEvent(
        run_id="test-run",
        step_id="test-step",
        event_type="test.event",
        payload={"data": "test"},
        event_id=str(uuid.uuid4())
    )
    
    # We need to subscribe to see the message (fakeredis handles this)
    pubsub = mock_redis.pubsub()
    pubsub.subscribe("test-step")
    
    bus.publish(event)
    
    # Check if the message was received on the channel
    # First message is usually the subscribe confirmation if ignore_subscribe_messages=False
    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
    if message is None:
        # Retry once for slow systems
        import time
        time.sleep(0.1)
        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
    
    assert message is not None
    
    # Message is now wrapped in a "sender_id" envelope
    data_wrapper = json.loads(message['data'])
    assert "sender_id" in data_wrapper
    data = data_wrapper['event']
    assert data['run_id'] == "test-run"
    assert data['event_type'] == "test.event"

def test_redis_event_bus_subscribe(mock_redis):
    """Verify that RedisEventBus correctly triggers callbacks on subscribed topics."""
    bus = RedisEventBus(redis_client=mock_redis)
    received_events = []
    
    def callback(event_dict):
        received_events.append(event_dict)
        
    bus.subscribe("test-step", callback)
    
    # Manually trigger a message through the worker thread simulation
    event_data = {
        "run_id": "test-run",
        "step_id": "test-step",
        "event_type": "test.event",
        "payload": {},
        "event_id": str(uuid.uuid4()),
        "created_at": "now",
        "attempt": 1
    }
    
    # Directly publish to the redis client to simulate an external process
    # Use the new envelope format
    message_data = {
        "sender_id": 999, # Different from current id(bus)
        "event": event_data
    }
    mock_redis.publish("test-step", json.dumps(message_data))
    
    # Wait for the background thread to process (fakeredis is fast, but let's give it a tiny moment)
    import time
    time.sleep(0.1)
    
    assert len(received_events) == 1
    assert received_events[0]['run_id'] == "test-run"

def test_redis_event_bus_global_subscriber(mock_redis):
    """Verify that global subscribers (like the logger) receive remote events."""
    bus = RedisEventBus(redis_client=mock_redis)
    received_events = []
    
    def global_callback(event_dict):
        received_events.append(event_dict)
        
    bus.subscribe("*", global_callback)
    
    event_data = {
        "run_id": "global-run",
        "step_id": "specific-step",
        "event_type": "remote.event",
        "payload": {},
        "event_id": str(uuid.uuid4()),
        "created_at": "now",
        "attempt": 1
    }
    
    # Simulate an external process publishing to 'specific-step'
    message_data = {
        "sender_id": 888,
        "event": event_data
    }
    mock_redis.publish("specific-step", json.dumps(message_data))
    
    import time
    time.sleep(0.2)
    
    assert any(e['run_id'] == "global-run" for e in received_events), "Global subscriber should have received the remote event"

def test_redis_event_bus_fallback():
    """Verify that we can toggle between Redis and InMemory buses."""
    from core.runtime.event_bus import get_event_bus
    
    with patch.dict(os.environ, {"USE_REDIS": "false"}):
        bus = get_event_bus()
        assert bus.__class__.__name__ == "EventBus"
        
    with patch.dict(os.environ, {"USE_REDIS": "true", "REDIS_URL": "redis://localhost:6379"}):
        # We need to mock the Redis client to avoid real connection attempts
        with patch('redis.from_url') as mock_from_url:
            mock_from_url.return_value = MagicMock()
            bus = get_event_bus()
            assert bus.__class__.__name__ == "RedisEventBus"
