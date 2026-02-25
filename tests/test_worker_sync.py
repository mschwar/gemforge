import json
import pytest
import fakeredis
import time
from unittest.mock import MagicMock, patch
from core.runtime.worker.daemon import DistributedWorker
from core.runtime.worker.dispatcher import OrchestratorDispatcher
from core.runtime.schema import StepEvent
from core.runtime.event_bus import RedisEventBus

@pytest.fixture
def mock_redis():
    return fakeredis.FakeRedis()

@pytest.fixture
def worker(mock_redis):
    # Create a RedisEventBus with the mock client
    bus = RedisEventBus(redis_client=mock_redis)
    with patch('core.runtime.worker.daemon.event_bus', bus):
        w = DistributedWorker("test-worker", ["qa"])
        yield w
        w.stop()

def test_worker_heartbeat(mock_redis, worker):
    """Verify that starting a worker registers it in Redis with a heartbeat."""
    worker.start()
    
    # Give it a moment to run the first heartbeat
    time.sleep(0.5)
    
    # Check redis for worker registration
    workers = mock_redis.hgetall("gemforge:workers")
    assert b"test-worker" in workers
    
    # Check if the heartbeat key exists
    heartbeat = mock_redis.get("gemforge:worker:test-worker:heartbeat")
    assert heartbeat is not None

def test_worker_state_patch_merge(mock_redis):
    """Verify that dispatcher correctly merges worker patches into the graph command."""
    mock_app = MagicMock()
    dispatcher = OrchestratorDispatcher(mock_app)
    
    event = StepEvent(
        run_id="test-thread",
        step_id="qa",
        event_type="worker.completed",
        payload={
            "state_patch": {"tests_passed": True},
            "metrics": {"duration_sec": 1.5}
        }
    )
    
    dispatcher._handle_worker_reply(event)
    
    # Verify app.invoke was called with a Command containing the patch
    args, kwargs = mock_app.invoke.call_args
    command = args[0]
    config = args[1]
    
    assert config["configurable"]["thread_id"] == "test-thread"
    assert command.resume["state_patch"]["tests_passed"] is True
    assert command.resume["metrics"]["duration_sec"] == 1.5

def test_worker_full_state_retrieval(mock_redis):
    """Verify that a worker can request full state from the orchestrator."""
    bus = RedisEventBus(redis_client=mock_redis)
    
    # Mock the app
    mock_app = MagicMock()
    # Mock get_state to return a full state
    mock_app.get_state.return_value = MagicMock(values={
        "run_id": "full-run", 
        "raw_idea": "full idea", 
        "repo_path": "/tmp/full",
        "selected_platform": "nextjs"
    })
    
    with patch('core.runtime.worker.daemon.event_bus', bus), \
         patch('core.runtime.worker.dispatcher.event_bus', bus):
        
        worker = DistributedWorker("test-worker", ["qa"])
        dispatcher = OrchestratorDispatcher(mock_app)
        
        # 1. Orchestrator requests work with partial state
        request_event = StepEvent(
            run_id="full-run",
            step_id="qa",
            event_type="step.requested",
            payload={"state_slice": {"run_id": "full-run"}, "is_partial": True}
        )
        
        # We need to capture the worker's response
        received_replies = []
        bus.subscribe("worker.completed", lambda e: received_replies.append(e))
        
        # Trigger the request
        with patch('core.pipeline_stages.nodes.qa_nodes.run_tests') as mock_run_tests:
            mock_run_tests.return_value = {"success": True, "report": "All tests passed", "failures": 0}
            worker._handle_request(request_event)
        
        # The worker should have:
        # 1. Seen is_partial=True
        # 2. Published state.requested
        # 3. Dispatcher should have replied with state.delivered
        # 4. Worker should have proceeded with full state
        
        # Wait for async processing
        time.sleep(0.5)
        
        assert len(received_replies) == 1
        # The worker should have had access to repo_path from the full state
        assert mock_app.get_state.called
