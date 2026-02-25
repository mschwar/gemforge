import functools
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

from langgraph.types import interrupt
from langgraph.errors import GraphInterrupt

from core.runtime.event_bus import event_bus
from core.runtime.schema import StepEvent
from core.runtime.logging import logger
from core.runtime.errors import handle_io_error
from core.build.cache import build_cache
from core.build.hasher import calculate_dir_hash, calculate_file_hash, calculate_string_hash
from core.build.taint_manager import taint_manager
from tools.cost_tracker import cost_tracker
from state import PipelineState

NODE_PROMPT_MAP = {
    "vision_polisher": "01_vision_polisher.md",
    "ruthless_interrogator": "02_ruthless_interrogator.md",
    "uiux": "04_uiux_design.md",
    "architecture": "05_architecture.md",
    "platform_decision": "05b_platform_decision.md",
    "frontend": "06_frontend.md",
    "backend": "07_backend.md",
    "data": "08_data.md",
    "infra": "10_infra.md",
    "cicd": "11_cicd.md",
    "sre": "12_sre.md",
    "director": "13_director.md",
    "qa_generator": "19_qa_generator.md",
    "weaver": "21_weaver_reflector.md",
    "repair": "22_iteration_surgeon.md",
    "business_strategist": "23_business_strategist.md",
    "landing_page": "24_landing_page_generator.md",
}

def _calculate_input_hash(state: PipelineState, step_id: str) -> str:
    """Calculates a deterministic hash of the inputs relevant to a step."""
    # Base inputs for almost all nodes
    inputs = {
        "raw_idea": state.get("raw_idea", ""),
        "source_docs_path": state.get("source_docs_path", ""),
        "step_id": step_id
    }
    
    # Add step-specific prompt hash
    prompt_file = NODE_PROMPT_MAP.get(step_id)
    if prompt_file:
        try:
            prompt_path = Path("agents") / prompt_file
            if prompt_path.exists():
                inputs["prompt_hash"] = calculate_file_hash(prompt_path)
        except Exception:
            pass

    # Add step-specific dependencies
    if step_id in ["vision_polisher", "ruthless_interrogator"]:
        inputs["audited_context"] = state.get("audited_context", "")
    
    if step_id == "vision_polisher":
        inputs["human_feedback"] = state.get("human_feedback", "")
        
    if step_id in ["frontend", "backend", "data", "qa_generator", "code_orchestrator"]:
        inputs["polished_vision"] = state.get("polished_vision", "")
        inputs["selected_platform"] = state.get("selected_platform", "")
        # Also incorporate the actual spec files if they exist on disk
        repo_path = state.get("repo_path")
        if repo_path and os.path.exists(repo_path):
            inputs["dir_hash"] = calculate_dir_hash(Path(repo_path))

    # Serialize and hash
    serialized = json.dumps(inputs, sort_keys=True)
    return calculate_string_hash(serialized)

def logged_node(node_func: Callable) -> Callable:
    """Decorator to publish step lifecycle events with metrics to the EventBus."""
    @functools.wraps(node_func)
    def wrapper(state: PipelineState, *args, **kwargs):
        from core.llm import current_node_id, node_usage_stats
        run_id = state.get("run_id", "unknown-run")
        step_id = node_func.__name__.replace("_node", "")
        
        # Initialize node-scoped usage tracking
        usage_token = node_usage_stats.set({"tokens": 0, "cost": 0.0})
        node_id_token = current_node_id.set(step_id)

        # 0. Cache Check
        input_hash = _calculate_input_hash(state, step_id)
        use_cache = os.getenv("GEMFORGE_USE_CACHE", "true").lower() == "true"
        is_tainted = taint_manager.is_tainted(run_id, step_id)
        
        if use_cache and not is_tainted:
            cached_result = build_cache.get(input_hash, step_id)
            if cached_result:
                logger.info(f"Node {step_id} cache hit (functional).", extra={"run_id": run_id, "step_id": step_id, "cache_hit": True})
                cached_result["_from_cache"] = True
                return cached_result

        # 1. Routing Logic (Strangler/Worker Proxy)
        is_worker = os.getenv("GEMFORGE_IS_WORKER", "false").lower() == "true"
        worker_enabled = os.getenv("GEMFORGE_WORKER_ENABLED", "false").lower() == "true"
        enabled_steps = os.getenv("GEMFORGE_WORKER_ENABLED_STEPS", "").split(",")
        
        should_proxy = (
            worker_enabled and 
            not is_worker and 
            (step_id in enabled_steps or "all" in enabled_steps)
        )
        
        if should_proxy:
            logger.info(f"Routing {step_id} to worker...", extra={"run_id": run_id, "step_id": step_id, "proxy": True})
            event_bus.publish(StepEvent(
                run_id=run_id,
                step_id=step_id,
                event_type="step.requested",
                payload={"state_slice": dict(state)}
            ))
            
            timeout_sec = int(os.getenv("GEMFORGE_WORKER_TIMEOUT", "300"))
            decision = interrupt({
                "action": "wait_for_worker", 
                "step_id": step_id,
                "timeout_at": time.time() + timeout_sec
            })
            
            if decision.get("status") == "failed":
                return handle_io_error(state, Exception(decision.get("error", "Unknown worker error")), step_id, error_code="WORKER_FAILURE")

            patch = decision.get("state_patch", {})
            metrics = decision.get("metrics", {})
            
            if metrics:
                cost_tracker.total_tokens += metrics.get("tokens_used", 0)
                cost_tracker.total_cost += metrics.get("cost_usd", 0.0)
                patch["total_tokens"] = metrics.get("tokens_used", 0)
                patch["total_cost"] = metrics.get("cost_usd", 0.0)

            if use_cache:
                build_cache.set(input_hash, step_id, patch)
            if is_tainted:
                taint_manager.clear_taint(run_id, step_id)

            return patch

        # 2. Execution Logic
        # 2a. Budget Check
        current_tokens = state.get("total_tokens", 0)
        current_cost = state.get("total_cost", 0.0)
        max_tokens = state.get("max_tokens", 1_000_000)
        max_cost = state.get("max_cost_usd", 50.0)
        
        if current_tokens > max_tokens:
            raise ValueError(f"CRITICAL: Token budget exceeded ({current_tokens} > {max_tokens}). Halting.")
        if current_cost > max_cost:
            raise ValueError(f"CRITICAL: Cost budget exceeded (${current_cost:.2f} > ${max_cost:.2f}). Halting.")

        start_time = time.time()

        event_bus.publish(StepEvent(
            run_id=run_id,
            step_id=step_id,
            event_type="step.started"
        ))
        logger.info(f"Node {step_id} started.", extra={"run_id": run_id, "step_id": step_id})
        
        try:
            result = node_func(state, *args, **kwargs)
            duration = time.time() - start_time
            
            usage = node_usage_stats.get()
            tokens_used = usage["tokens"]
            cost_incurred = usage["cost"]

            if isinstance(result, dict):
                result["total_tokens"] = tokens_used
                result["total_cost"] = cost_incurred

            if use_cache:
                build_cache.set(input_hash, step_id, result)
            if is_tainted:
                taint_manager.clear_taint(run_id, step_id)

            event_bus.publish(StepEvent(
                run_id=run_id,
                step_id=step_id,
                event_type="step.completed",
                payload={
                    "result_keys": list(result.keys()) if isinstance(result, dict) else [],
                    "metrics": {
                        "duration_sec": round(duration, 3),
                        "tokens_used": tokens_used,
                        "cost_usd": round(cost_incurred, 6)
                    }
                }
            ))
            return result
        except GraphInterrupt as e:
            raise e
        except Exception as e:
            duration = time.time() - start_time
            event_bus.publish(StepEvent(
                run_id=run_id,
                step_id=step_id,
                event_type="step.failed",
                payload={"error": str(e), "metrics": {"duration_sec": round(duration, 3)}}
            ))
            raise e
        finally:
            node_usage_stats.reset(usage_token)
            current_node_id.reset(node_id_token)
    return wrapper
