import asyncio
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import AsyncGenerator, Dict, List

from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse

from core.runtime.event_bus import event_bus
from core.runtime.event_logger import event_logger

app = FastAPI(title="GemForge Runtime API")
_DB_PATH = Path(__file__).resolve().parent.parent.parent / "checkpoints.db"

# ... event_queues and event_bus_callback ...

@app.get("/runs")
async def list_runs(limit: int = 10):
    """List recent pipeline runs."""
    return {"runs": event_logger.get_recent_runs(limit=limit)}

@app.get("/runs/{run_id}/events")
async def get_run_events(run_id: str):
    """Get all historical events for a run."""
    return {"events": event_logger.get_run_events(run_id)}

@app.get("/runs/{run_id}/repairs")
async def get_run_repairs(run_id: str):
    """Get repair history for a run."""
    with sqlite3.connect(str(_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM repair_attempts WHERE run_id = ? ORDER BY created_at ASC", (run_id,))
        return {"repairs": [dict(row) for row in cur.fetchall()]}

@app.get("/runs/{run_id}/stream")
async def stream_run_events(run_id: str, request: Request):
    """SSE stream of events for a specific run."""
    async def event_generator() -> AsyncGenerator:
        q = asyncio.Queue()
        event_queues.append(q)
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                
                event_dict = await q.get()
                
                # Filter by run_id if specified (or stream all)
                if run_id == "all" or event_dict.get("run_id") == run_id:
                    yield {
                        "event": "step_update",
                        "id": event_dict.get("event_id"),
                        "data": json.dumps(event_dict)
                    }
        finally:
            event_queues.remove(q)

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
