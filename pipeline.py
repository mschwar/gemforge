from dotenv import load_dotenv

load_dotenv()

import json
import os
import re
import sqlite3
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from core.llm import cost_aware_invoke, load_prompt
from core.pipeline_stages.context_builders import (
    build_ops_context as stage_build_ops_context,
    build_parallel_context as stage_build_parallel_context,
)
from core.pipeline_stages.failure_semantics import (
    build_deploy_result,
    build_git_publish_result,
    build_missing_repo_publish_result,
    route_after_git_publish_state,
    route_after_review_state,
)
from state import PipelineState
from tools.deploy_tools import deploy_to_vercel
from tools.executor_tools import run_tests
from tools.file_tools import create_project_structure, write_file
from tools.git_tools import push_to_github
from tools.project_tools import (
    apply_template,
    generate_xcode_project,
    parse_platform_manifest,
)


def parse_and_save_docs(response_text: str, repo_path: str) -> tuple[dict, list[Path]]:
    """Parse ===FILENAME=== blocks and write each to disk.
    Returns (dict_of_excerpts, list_of_written_paths).
    """
    saved = {}
    saved_paths = []
    repo_root = Path(repo_path).resolve()
    pattern = r"===([^=\n]+?)===\n(.*?)(?=\n===|\Z)"
    matches = re.findall(pattern, response_text, re.DOTALL)
    for filename, content in matches:
        filename = filename.strip()
        # Ignore fenced-code-block language tags that look like ===python===
        if not any(filename.endswith(ext) for ext in (".md", ".txt", ".yml", ".yaml", ".html", ".json")) \
                and "/" not in filename:
            continue

        # Guard: block model-suggested paths that escape the project directory.
        destination = (repo_root / filename).resolve()
        try:
            destination.relative_to(repo_root)
        except ValueError:
            print(f"   ⚠️ SECURITY: Rejected path traversal attempt in docs output: {filename!r}")
            continue

        write_file(str(destination), content.strip())
        saved[filename] = content.strip()[:200]
        saved_paths.append(destination)
        print(f"   → Saved {filename}")
    return saved, saved_paths

from tools.ingestor_tools import bundle_context
from core.runtime.event_bus import event_bus
from core.runtime.schema import StepEvent
from core.memory.semantic_index import semantic_indexer
from core.memory.retriever import semantic_retriever
from core.repair.agentic_loop import repair_node
from core.build.hasher import calculate_string_hash, calculate_dir_hash, calculate_file_hash
from core.build.cache import build_cache
from core.build.taint_manager import taint_manager
import functools

def _calculate_input_hash(state: PipelineState, step_id: str) -> str:
    """Calculates a deterministic hash of the inputs relevant to a step."""
    # Base inputs for almost all nodes
    inputs = {
        "raw_idea": state.get("raw_idea", ""),
        "source_docs_path": state.get("source_docs_path", ""),
        "step_id": step_id
    }
    
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

from langgraph.errors import GraphInterrupt
from tools.cost_tracker import cost_tracker
import time

def logged_node(node_func):
    """Decorator to publish step lifecycle events with metrics to the EventBus.
    
    If GEMFORGE_WORKER_ENABLED is true and the step is enabled, this decorator
    acts as a proxy: it publishes a 'step.requested' event and interrupts
    the orchestrator.
    """
    @functools.wraps(node_func)
    def wrapper(state: PipelineState, *args, **kwargs):
        run_id = state.get("run_id", "unknown-run")
        step_id = node_func.__name__.replace("_node", "")
        
        # 0. Cache Check (Phase 1)
        input_hash = _calculate_input_hash(state, step_id)
        use_cache = os.getenv("GEMFORGE_USE_CACHE", "true").lower() == "true"
        is_tainted = taint_manager.is_tainted(run_id, step_id)
        
        if use_cache and not is_tainted:
            cached_result = build_cache.get(input_hash, step_id)
            if cached_result:
                # Add a marker so we know it was cached
                cached_result["_from_cache"] = True
                return cached_result

        if is_tainted:
            print(f"   🚩 [BUILD] Node {step_id} is stale (tainted). Bypassing cache.")

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
            print(f"   📡 [PROXY] Routing {step_id} to worker...")
            event_bus.publish(StepEvent(
                run_id=run_id,
                step_id=step_id,
                event_type="step.requested",
                payload={"state_slice": dict(state)}
            ))
            # Suspend graph execution
            # The dispatcher will resume this node with Command(resume={"state_patch": ..., "metrics": ...})
            decision = interrupt({"action": "wait_for_worker", "step_id": step_id})
            
            # Apply patch and update orchestrator cost tracking
            patch = decision.get("state_patch", {})
            metrics = decision.get("metrics", {})
            
            if metrics:
                # Sync the worker's consumption back to the orchestrator counters
                cost_tracker.total_tokens += metrics.get("tokens_used", 0)
                cost_tracker.total_cost += metrics.get("cost_usd", 0.0)
                
                # Also update the state dict itself
                patch["total_tokens"] = state.get("total_tokens", 0) + metrics.get("tokens_used", 0)
                patch["total_cost"] = state.get("total_cost", 0.0) + metrics.get("cost_usd", 0.0)

            # Store the worker's result in cache
            if use_cache:
                build_cache.set(input_hash, step_id, patch)
            
            # Clear taint if it was tainted
            if is_tainted:
                taint_manager.clear_taint(run_id, step_id)

            return patch

        # 2. Execution Logic (Standard Sync or inside Worker)
        start_time = time.time()
        start_tokens = cost_tracker.total_tokens
        start_cost = cost_tracker.total_cost

        # Publish: step.started
        event_bus.publish(StepEvent(
            run_id=run_id,
            step_id=step_id,
            event_type="step.started"
        ))
        
        try:
            result = node_func(state, *args, **kwargs)
            
            duration = time.time() - start_time
            tokens_used = cost_tracker.total_tokens - start_tokens
            cost_incurred = cost_tracker.total_cost - start_cost

            # Store result in cache
            if use_cache:
                build_cache.set(input_hash, step_id, result)
            
            # Clear taint if it was tainted
            if is_tainted:
                taint_manager.clear_taint(run_id, step_id)

            # Publish: step.completed
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
            # Re-raise without logging as failure (it's a pause, not an error)
            raise e
        except Exception as e:
            duration = time.time() - start_time
            # Publish: step.failed
            event_bus.publish(StepEvent(
                run_id=run_id,
                step_id=step_id,
                event_type="step.failed",
                payload={
                    "error": str(e),
                    "metrics": {
                        "duration_sec": round(duration, 3)
                    }
                }
            ))
            raise e
    return wrapper


# ====================== NODES ======================

@logged_node
def document_auditor_node(state: PipelineState):
    path = state.get("source_docs_path")
    if not path or not os.path.exists(path):
        print("⏭️  Skipping Document Auditor (no path provided)")
        return {"audited_context": None}

    print(f"🔨 0. Document Auditor sifting through {path}...")
    context_bundle, context_stats = bundle_context(
        path,
        raw_idea=state.get("raw_idea", ""),
        include_stats=True,
    )
    print(
        "   → Context bundle: "
        f"{context_stats['included_files']} files, "
        f"{context_stats['total_chars']} chars, "
        f"~{context_stats['estimated_tokens']} tokens"
    )
    if context_stats["dropped_by_budget"] or context_stats["dropped_oversized_file"]:
        print(
            "   ⚠️ Context budget trimming: "
            f"dropped={context_stats['dropped_by_budget']}, "
            f"oversized={context_stats['dropped_oversized_file']}, "
            f"truncated={context_stats['truncated_files']}"
        )
    
    prompt = load_prompt("28_document_auditor.md")
    user_content = f"DIRECTORY_CONTEXT:\n\n{context_bundle}\n\nRAW_IDEA: {state['raw_idea']}"
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=user_content)]
    response = cost_aware_invoke(messages)
    
    print("   → Audit complete. Nucleus extracted.")
    return {
        "audited_context": response.content,
        "progress_log": [
            "✅ Document Audit complete",
            "📊 CONTEXT_BUDGET "
            + json.dumps(
                {
                    "included_files": context_stats["included_files"],
                    "dropped_by_budget": context_stats["dropped_by_budget"],
                    "dropped_oversized_file": context_stats["dropped_oversized_file"],
                    "truncated_files": context_stats["truncated_files"],
                    "estimated_tokens": context_stats["estimated_tokens"],
                },
                sort_keys=True,
            ),
        ],
    }

@logged_node
def vision_polisher_node(state: PipelineState):
    print("🔨 1. Vision Polisher running...")
    prompt = load_prompt("01_vision_polisher.md")
    feedback = state.get("human_feedback")
    audited = state.get("audited_context")
    
    if feedback:
        user_content = (
            f"Raw Idea: {state['raw_idea']}\n\n"
            f"Previous polished vision:\n{state['polished_vision']}\n\n"
            f"User feedback: {feedback}\n\nPlease refine the vision based on this feedback."
        )
    elif audited:
        user_content = (
            f"Raw Idea: {state['raw_idea']}\n\n"
            f"DOCUMENT_AUDIT_NUCLEUS:\n{audited}\n\n"
            "Please incorporate the audit findings into the polished vision."
        )
    else:
        user_content = f"Raw Idea: {state['raw_idea']}"
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=user_content)]
    response = cost_aware_invoke(messages)
    print("   → Polished vision ready for approval")
    return {
        "polished_vision": response.content,
        "approval_status": "pending",
        "human_feedback": None,
        "progress_log": ["✅ Vision Polisher completed"],
    }

@logged_node
def human_review_node(state: PipelineState):
    print("\n" + "─" * 80)
    print("  POLISHED VISION")
    print("─" * 80)
    print(state.get("polished_vision", ""))
    print("─" * 80)
    print("\n⏸️  HUMAN APPROVAL GATE — pipeline is paused.")
    print()
    print("  Run one of these commands to continue:")
    print("    python resume.py approve")
    print("    python resume.py refine \"Your feedback here\"")
    print()
    decision = interrupt("Review the polished vision. Approve or request refinements.")
    updates = {"approval_status": decision.get("action", "pending")}
    if decision.get("feedback"):
        updates["human_feedback"] = decision["feedback"]
    return updates

@logged_node
def ruthless_interrogator_node(state: PipelineState):
    print("🔨 2. Ruthless Interrogator generating canonical docs...")
    prompt = load_prompt("02_ruthless_interrogator.md")
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"POLISHED_VISION:\n\n{state['polished_vision']}\n\nGenerate all canonical docs now.")
    ]
    response = cost_aware_invoke(messages)
    return {
        "canonical_docs": {"_raw_output": response.content},
        "progress_log": ["✅ Canonical docs generated"],
    }

def _index_files(run_id: str, project_name: str, paths: list[Path], doc_type: str = "source"):
    """Helper to index multiple files in the semantic memory."""
    for path in paths:
        try:
            semantic_indexer.index_file(run_id, project_name, path, doc_type)
        except Exception as e:
            print(f"   ⚠️ Semantic Indexing failed for {path.name}: {e}")

@logged_node
def bootstrapper_node(state: PipelineState):
    print("🔨 3. Bootstrapper creating REAL project...")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    repo_path = create_project_structure(gem_name)

    # Write the Staff Audit if it exists
    audited = state.get("audited_context")
    if audited and repo_path:
        write_file(f"{repo_path}/STAFF_AUDIT.md", audited)
        print("   → STAFF_AUDIT.md saved to repo")
        # Index the staff audit
        _index_files(state["run_id"], gem_name, [Path(repo_path) / "STAFF_AUDIT.md"], "audit")

    # Write canonical docs now that the folder exists
    raw_output = state.get("canonical_docs", {}).get("_raw_output", "")
    if raw_output:
        saved, saved_paths = parse_and_save_docs(raw_output, repo_path)
        canonical_docs = saved if saved else {"INTERROGATION.md": raw_output[:200]}
        if not saved:
            p = Path(repo_path) / "INTERROGATION.md"
            write_file(str(p), raw_output)
            saved_paths = [p]
        
        # Index canonical docs
        _index_files(state["run_id"], gem_name, saved_paths, "spec")
    else:
        canonical_docs = {}

    print(f"   → Project ready: {repo_path}")
    
    # 4. Generate Build Manifest (Phase 0)
    manifest = {
        "project_name": gem_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bootstrap_hash": calculate_dir_hash(Path(repo_path)),
        "files": {
            str(p.relative_to(repo_path)): calculate_file_hash(p)
            for p in Path(repo_path).glob("*") if p.is_file() and not p.name.startswith(".")
        }
    }
    write_file(f"{repo_path}/BUILD_MANIFEST.json", json.dumps(manifest, indent=2))

    return {
        "repo_path": repo_path,
        "repo_created": True,
        "canonical_docs": canonical_docs,
        "progress_log": [f"✅ Repo + docs at {repo_path}"],
    }

@logged_node
def uiux_node(state: PipelineState):
    print("🔨 4. UI/UX Design Agent running...")
    prompt = load_prompt("04_uiux_design.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"STAFF_AUDIT:\n{state.get('audited_context', 'N/A')}\n\n"
        + "\n".join(f"{k}: {v}" for k, v in state.get("canonical_docs", {}).items() if not k.startswith("_"))
    )
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Project context:\n\n{context}")]
    response = cost_aware_invoke(messages)
    if repo_path:
        p = Path(repo_path) / "UIUX_SPEC.md"
        write_file(str(p), response.content)
        print("   → UIUX_SPEC.md saved")
        _index_files(state["run_id"], gem_name, [p], "spec")
    return {"progress_log": ["✅ UI/UX spec complete"]}

@logged_node
def architecture_node(state: PipelineState):
    print("🔨 5. Architecture Agent running...")
    prompt = load_prompt("05_architecture.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"STAFF_AUDIT:\n{state.get('audited_context', 'N/A')}\n\n"
        + "\n".join(f"{k}: {v}" for k, v in state.get("canonical_docs", {}).items() if not k.startswith("_"))
    )
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Project context:\n\n{context}")]
    response = cost_aware_invoke(messages)
    if repo_path:
        p = Path(repo_path) / "ARCHITECTURE.md"
        write_file(str(p), response.content)
        print("   → ARCHITECTURE.md saved")
        _index_files(state["run_id"], gem_name, [p], "spec")
    return {"architecture_complete": True, "progress_log": ["✅ Architecture complete"]}

@logged_node
def business_strategist_node(state: PipelineState):
    print("🔨 5c. Business Strategist Agent running...")
    prompt = load_prompt("23_business_strategist.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    
    # Context includes the primary docs for business alignment
    docs = state.get("canonical_docs", {})
    context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"PRD:\n{docs.get('PRD.md', 'N/A')}\n"
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=context)]
    response = cost_aware_invoke(messages)
    
    if repo_path:
        # Use our standard doc parser to save BUSINESS_STRATEGY.md
        saved, saved_paths = parse_and_save_docs(response.content, repo_path)
        if not saved:
             p = Path(repo_path) / "BUSINESS_STRATEGY.md"
             write_file(str(p), response.content)
             saved_paths = [p]
        print("   → BUSINESS_STRATEGY.md saved")
        _index_files(state["run_id"], gem_name, saved_paths, "spec")
        
    return {"business_strategy_complete": True, "progress_log": ["✅ Business strategy complete"]}

@logged_node
def landing_page_node(state: PipelineState):
    print("🔨 5d. Landing Page Agent running...")
    prompt = load_prompt("24_landing_page_generator.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    
    # Context includes the primary docs for landing page alignment
    strategy_path = f"{repo_path}/BUSINESS_STRATEGY.md"
    strategy_content = ""
    if os.path.exists(strategy_path):
        with open(strategy_path) as f:
            strategy_content = f.read()

    context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"BUSINESS_STRATEGY:\n{strategy_content}\n"
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=context)]
    response = cost_aware_invoke(messages)
    
    if repo_path:
        # Use our standard doc parser to save LANDING_PAGE.html
        saved, saved_paths = parse_and_save_docs(response.content, repo_path)
        if not saved:
             p = Path(repo_path) / "LANDING_PAGE.html"
             write_file(str(p), response.content)
             saved_paths = [p]
        print("   → LANDING_PAGE.html saved")
        _index_files(state["run_id"], gem_name, saved_paths, "spec")
        
    return {"landing_page_complete": True, "progress_log": ["✅ Landing page complete"]}

@logged_node
def platform_decision_node(state: PipelineState):
    print("🔨 5b. Platform Decision Agent running...")
    prompt = load_prompt("05b_platform_decision.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    polished_vision = state.get("polished_vision", "")
    arch_content = ""
    try:
        arch_path = f"{repo_path}/ARCHITECTURE.md"
        with open(arch_path, encoding="utf-8") as f:
            arch_content = f.read()
    except Exception:
        pass
    context = f"POLISHED_VISION:\n{polished_vision}\n\nARCHITECTURE:\n{arch_content}"
    messages = [SystemMessage(content=prompt), HumanMessage(content=context)]
    response = cost_aware_invoke(messages)
    manifest_data = parse_platform_manifest(response.content)
    if repo_path:
        p = Path(repo_path) / "PLATFORM_MANIFEST.md"
        write_file(str(p), response.content)
        print("   → PLATFORM_MANIFEST.md saved")
        _index_files(state["run_id"], gem_name, [p], "spec")
    return {
        "selected_platform": manifest_data.get("selected_platform", ""),
        "selected_template": manifest_data.get("template", ""),
        "platform_manifest": manifest_data,
        "progress_log": [
            "✅ Platform decision complete",
            (
                f"   ↳ platform={manifest_data.get('selected_platform', 'unknown')}, "
                f"template={manifest_data.get('template', 'unknown')}"
            ),
        ],
    }

@logged_node
def code_orchestrator_node(state: PipelineState):
    print("🔨 6. Code Generation Orchestrator — launching real generators...")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    from tools.executor_tools import build_and_verify_xcode, parse_and_save_generated_code

    manifest_path = f"{repo_path}/PLATFORM_MANIFEST.md"
    manifest_content = ""
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as manifest_file:
            manifest_content = manifest_file.read()
    manifest_data = parse_platform_manifest(manifest_content)

    template_hint = (
        manifest_data.get("template")
        or manifest_data.get("selected_platform")
        or state.get("selected_template")
    )
    
    if not template_hint:
        raise ValueError("CRITICAL: Platform Decision Agent failed to produce a valid template selection.")

    template_result = apply_template(repo_path, template_hint)
    template_metadata = template_result.get("metadata", {})
    selected_platform = template_result.get("platform", template_hint)
    supports_llm_generators = bool(template_metadata.get("supports_llm_generators", False))

    progress = [f"✅ Template applied: {template_result.get('name')} ({selected_platform})"]

    def _safe_read(path: str) -> str:
        try:
            with open(path, encoding="utf-8") as file:
                return file.read()
        except Exception:
            return ""

    generator_context = (
        f"POLISHED_VISION:\n{state.get('polished_vision', '')}\n\n"
        f"STAFF_AUDIT:\n{state.get('audited_context', 'N/A')}\n\n"
        f"UIUX_SPEC:\n{_safe_read(f'{repo_path}/UIUX_SPEC.md')}\n\n"
        f"ARCHITECTURE:\n{_safe_read(f'{repo_path}/ARCHITECTURE.md')}\n\n"
        f"PLATFORM_MANIFEST:\n{manifest_content}"
    )

    if supports_llm_generators:
        min_generator_writes = max(1, int(os.getenv("GEMFORGE_MIN_GENERATOR_WRITES", "1")))
        generator_write_counts = {}

        # 1. UI Code Generator
        prompt = load_prompt("16_ui_code_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        ui_response = cost_aware_invoke(messages)
        ui_paths = parse_and_save_generated_code(
            repo_path,
            ui_response.content,
        )
        generator_write_counts["ui_code_generator"] = len(ui_paths)
        _index_files(state["run_id"], gem_name, ui_paths, "source")

        # 2. Core Logic Generator
        prompt = load_prompt("17_core_logic_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        logic_response = cost_aware_invoke(messages)
        logic_paths = parse_and_save_generated_code(
            repo_path,
            logic_response.content,
        )
        generator_write_counts["core_logic_generator"] = len(logic_paths)
        _index_files(state["run_id"], gem_name, logic_paths, "source")

        # 3. Platform-Specific Generator
        prompt = load_prompt("18_platform_specific_generator.md")
        messages = [SystemMessage(content=prompt), HumanMessage(content=generator_context)]
        platform_response = cost_aware_invoke(messages)
        platform_paths = parse_and_save_generated_code(
            repo_path,
            platform_response.content,
        )
        generator_write_counts["platform_specific_generator"] = len(platform_paths)
        _index_files(state["run_id"], gem_name, platform_paths, "source")

        malformed_generators = [
            name for name, writes in generator_write_counts.items() if writes < min_generator_writes
        ]
        if malformed_generators:
            error_payload = {
                "error_code": "GENERATOR_OUTPUT_MALFORMED",
                "min_generator_writes": min_generator_writes,
                "generator_write_counts": generator_write_counts,
                "malformed_generators": malformed_generators,
            }
            if repo_path:
                write_file(
                    f"{repo_path}/GENERATOR_FAILURE.json",
                    json.dumps(error_payload, indent=2, sort_keys=True),
                )
            print(f"   ❌ GENERATOR_OUTPUT_MALFORMED: {json.dumps(error_payload, sort_keys=True)}")
            raise ValueError(f"GENERATOR_OUTPUT_MALFORMED::{json.dumps(error_payload, sort_keys=True)}")

        progress.append(f"✅ LLM code generators completed ({generator_write_counts})")
    else:
        progress.append("✅ Template-only code path selected (no LLM generators)")

    # 4. Project structure / build verification
    if selected_platform == "ios-swiftui":
        app_name = template_result.get("context", {}).get("APP_NAME_SAFE", "GemForgeApp")
        generate_xcode_project(repo_path, app_name)
        build_and_verify_xcode(repo_path)
        progress.append("✅ iOS project structure + build verification complete")
    else:
        validation = template_result.get("validation", {})
        if validation.get("valid", False):
            progress.append("✅ Template validation complete")
        else:
            progress.append(
                f"⚠️ Template validation missing files: {validation.get('missing_files', [])}"
            )

    return {
        "selected_platform": selected_platform,
        "selected_template": template_result.get("name"),
        "platform_manifest": manifest_data,
        "progress_log": progress,
    }

# ---- PARALLEL AGENTS (return only changed keys — required for parallel execution) ----

def _build_parallel_context(state: PipelineState) -> str:
    vision = state.get("polished_vision", "")
    
    # RAG: Retrieve relevant past examples
    rag_context = ""
    try:
        # Search for similar historical chunks
        past_examples = semantic_retriever.search(vision, k=3)
        if past_examples:
            rag_context = "\n### RELEVANT PAST EXAMPLES (FOR CONTEXT):\n"
            for i, ex in enumerate(past_examples):
                rag_context += f"\n-- Example {i+1} (Project: {ex['metadata'].get('project_name', 'Unknown')}) --\n"
                rag_context += ex["text"] + "\n"
    except Exception as e:
        print(f"   ⚠️ RAG retrieval failed: {e}")

    return stage_build_parallel_context(state, extra_context=rag_context)

@logged_node
def frontend_node(state: PipelineState):
    print("🔨 7. Frontend Agent (parallel)...")
    prompt = load_prompt("06_frontend.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    context = _build_parallel_context(state)
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    if repo_path:
        p = Path(repo_path) / "FRONTEND_SPEC.md"
        write_file(str(p), response.content)
        _index_files(state["run_id"], gem_name, [p], "spec")
    return {"frontend_complete": True, "progress_log": ["✅ Frontend spec complete"]}

@logged_node
def backend_node(state: PipelineState):
    print("🔨 8. Backend Agent (parallel)...")
    prompt = load_prompt("07_backend.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    context = _build_parallel_context(state)
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    if repo_path:
        p = Path(repo_path) / "BACKEND_SPEC.md"
        write_file(str(p), response.content)
        _index_files(state["run_id"], gem_name, [p], "spec")
    return {"backend_complete": True, "progress_log": ["✅ Backend spec complete"]}

@logged_node
def data_node(state: PipelineState):
    print("🔨 9. Data Architecture Agent (parallel)...")
    prompt = load_prompt("08_data.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    context = _build_parallel_context(state)
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    if repo_path:
        p = Path(repo_path) / "DATA_SPEC.md"
        write_file(str(p), response.content)
        _index_files(state["run_id"], gem_name, [p], "spec")
    return {"data_complete": True, "progress_log": ["✅ Data spec complete"]}

# ---- SEQUENTIAL CHAIN ----

def _ops_context(state: PipelineState) -> str:
    """Shared context for infra/cicd/sre agents."""
    return stage_build_ops_context(state)

@logged_node
def infra_node(state: PipelineState):
    print("🔨 10. Infrastructure Agent...")
    prompt = load_prompt("10_infra.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=_ops_context(state))])
    if repo_path:
        saved, saved_paths = parse_and_save_docs(response.content, repo_path)
        if not saved:
            p = Path(repo_path) / "INFRA.md"
            write_file(str(p), response.content)
            saved_paths = [p]
        print("   → Infrastructure spec saved")
        _index_files(state["run_id"], gem_name, saved_paths, "spec")
    return {"infra_complete": True, "progress_log": ["✅ Infra spec complete"]}

@logged_node
def cicd_node(state: PipelineState):
    print("🔨 11. CI/CD Agent...")
    prompt = load_prompt("11_cicd.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=_ops_context(state))])
    if repo_path:
        saved, saved_paths = parse_and_save_docs(response.content, repo_path)
        if not saved:
            p = Path(repo_path) / "CICD.md"
            write_file(str(p), response.content)
            saved_paths = [p]
        print("   → CI/CD spec saved")
        _index_files(state["run_id"], gem_name, saved_paths, "spec")
    return {"cicd_complete": True, "progress_log": ["✅ CI/CD spec complete"]}

@logged_node
def sre_node(state: PipelineState):
    print("🔨 12. SRE & Observability Agent...")
    prompt = load_prompt("12_sre.md")
    repo_path = state.get("repo_path", "")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=_ops_context(state))])
    if repo_path:
        saved, saved_paths = parse_and_save_docs(response.content, repo_path)
        if not saved:
            p = Path(repo_path) / "SRE.md"
            write_file(str(p), response.content)
            saved_paths = [p]
        print("   → SRE spec saved")
        _index_files(state["run_id"], gem_name, saved_paths, "spec")
    return {"sre_complete": True, "progress_log": ["✅ SRE spec complete"]}

@logged_node
def deploy_node(state: PipelineState):
    print("🔨 13. Final Deploy Agent...")
    repo_path = state.get("repo_path", "new-gem")
    selected_platform = str(state.get("selected_platform", "")).strip().lower()

    # Always use selected_platform for native detection — never raw idea text.
    # Passing idea text can misclassify web apps whose description mentions "iOS".
    live_url = deploy_to_vercel(repo_path, selected_platform)

    result = build_deploy_result(state, repo_path, selected_platform, live_url)
    if result.get("deploy_status") == "live":
        print(f"\n🎉 APP IS NOW LIVE → {result.get('live_url')}")
    elif result.get("deploy_status") == "local":
        print(f"\n📦 Native project ready locally at: {repo_path}")
    else:
        print(f"\n📦 Project ready locally at: {repo_path}")
    return result

# ====================== ROUTING ======================

def route_after_review(state: PipelineState) -> str:
    return route_after_review_state(state)


def route_after_qa(state: PipelineState) -> str:
    if state.get("tests_passed", False):
        return "director"
    
    # Bounded repair loop
    max_attempts = int(os.getenv("GEMFORGE_AUTO_REPAIR_MAX_ATTEMPTS", "3"))
    if state.get("repair_count", 0) < max_attempts:
        return "repair"
        
    return "director"


def route_after_git_publish(state: PipelineState) -> str:
    return route_after_git_publish_state(state)

# ====================== GRAPH ======================

# ====================== QA / TESTING NODES (Module 2 — Real QA Layer) ======================
@logged_node
def qa_generator_node(state: PipelineState):
    """19_qa_generator.md — generates platform-appropriate tests"""
    print("🧪 19. QA Generator running...")
    prompt = load_prompt("19_qa_generator.md")
    gem_name = state.get("raw_idea", "NewGem")[:50]
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Project at: {state['repo_path']}\nPlatform: {state['selected_platform']}\nGenerate tests now.")]
    response = cost_aware_invoke(messages)
    saved, saved_paths = parse_and_save_docs(response.content, state["repo_path"])
    _index_files(state["run_id"], gem_name, saved_paths, "test")
    return {
        "tests_generated": True,
        "test_report": "Tests generated — see TESTS_SUMMARY.md",
        "progress_log": [f"🧪 Generated tests for {state['selected_platform']}"]
    }

@logged_node
def qa_node(state: PipelineState):
    """Executes the tests via run_tests and decides pass/fail"""
    print("🧪 20. QA Executor running...")
    if not state.get("repo_path"):
        return {"tests_passed": False, "test_report": "No repo_path — skipping tests", "progress_log": ["⚠️ QA skipped (no repo)"]}
    test_result = run_tests(state["repo_path"], state["selected_platform"])
    return {
        "tests_passed": test_result["success"],
        "test_report": test_result["report"],
        "test_details": test_result.get("details", ""),
        "progress_log": [f"🧪 QA Result: {test_result['report']} ({test_result['failures']} failures)"]
    }


@logged_node
def director_node(state: PipelineState):
    print("🎬 20b. Director Review running...")
    prompt = load_prompt("13_director.md")
    repo_path = state.get("repo_path", "")
    
    def _safe_read(filename):
        try:
            with open(f"{repo_path}/{filename}", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return f"[{filename} not yet available]"

    context = (
        f"POLISHED_VISION:\n{state['polished_vision']}\n\n"
        f"ARCHITECTURE:\n{_safe_read('ARCHITECTURE.md')}\n\n"
        f"FRONTEND_SPEC:\n{_safe_read('FRONTEND_SPEC.md')}\n\n"
        f"BACKEND_SPEC:\n{_safe_read('BACKEND_SPEC.md')}\n\n"
        f"DATA_SPEC:\n{_safe_read('DATA_SPEC.md')}\n\n"
        f"QA_REPORT:\n{state.get('test_report', 'N/A')}"
    )
    
    response = cost_aware_invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    
    if repo_path:
        write_file(f"{repo_path}/DIRECTOR_REVIEW.md", response.content)
        print("   → DIRECTOR_REVIEW.md saved")
        
    is_green = "GREEN LIGHT" in response.content.upper()
    rejection_count = state.get("director_rejection_count", 0)
    tests_passed = bool(state.get("tests_passed", False))

    # QA is a hard gate: no green light when tests did not pass.
    if not tests_passed:
        is_green = False
        print("   ⚠️  QA gate failed — director approval blocked.")

    if not is_green:
        rejection_count += 1
        if rejection_count >= 3:
            print(f"   ⚠️  Director rejected {rejection_count} times — manual intervention required.")

    return {
        "director_approved": is_green,
        "director_rejection_count": rejection_count,
        "progress_log": [f"🎬 Director Verdict: {'✅ GREEN LIGHT' if is_green else '⚠️ CORRECTION REQUESTED'}"]
    }


# ====================== GIT PUBLISH NODE (Module 3) ======================
@logged_node
def git_publish_node(state: PipelineState):
    """20_git_publish.md — auto GitHub repo + push + PR"""
    print("📤 21. Git Publish running...")
    if not state.get("repo_path"):
        return build_missing_repo_publish_result()
    publish_result = push_to_github(state["repo_path"], state["raw_idea"])
    return build_git_publish_result(state, publish_result)


@logged_node
def shipping_node(state: PipelineState):
    """26_shipping_manifest_agent.md — auto-generates launch metadata and checklists"""
    print("🚀 23. Shipping Manifest (v2.0) running...")
    from core.shipping.shipper import shipper as launch_shipper
    
    repo_path = state.get("repo_path")
    if not repo_path:
        return {"shipping_complete": False, "progress_log": ["⚠️ Shipping skipped (no repo)"]}
        
    vision = state.get("polished_vision", "")
    platform = state.get("selected_platform", "Web")
    
    # Try to load strategy
    strategy_path = Path(repo_path) / "BUSINESS_STRATEGY.md"
    strategy = ""
    if os.path.exists(strategy_path):
        with open(strategy_path) as f:
            strategy = f.read()
            
    launch_shipper.prepare_launch_manifest(repo_path, vision, strategy, platform)
    
    return {
        "shipping_complete": True,
        "progress_log": ["🚀 Launchpad: SHIPPING_MANIFEST.md ready"]
    }


# ====================== WEAVER REFLECTION NODE (v2.0 Pillar 1+8) ======================
@logged_node
def weaver_node(state: PipelineState):
    """21_weaver_reflector.md — extracts lessons & updates user taste"""
    print("🕸️  22. Weaver Reflector (v2.0) running...")
    from core.evolution.iterator import IterationEngine
    from core.evolution.weaver import parse_and_log_weaver_output
    
    prompt = load_prompt("21_weaver_reflector.md")
    gem_id = state.get("raw_idea", "Unknown")[:30]
    
    # NEW: Gather actual code context so Weaver can see WHY things failed
    code_context = ""
    repo_path = state.get("repo_path")
    if repo_path and os.path.exists(repo_path):
        engine = IterationEngine()
        code_context = engine.get_project_context(Path(repo_path).name)

    # Collect context for the Weaver
    context = (
        f"RAW_IDEA: {state.get('raw_idea')}\n"
        f"POLISHED_VISION: {state.get('polished_vision')}\n"
        f"HUMAN_FEEDBACK: {state.get('human_feedback')}\n"
        f"REPAIR_HISTORY: {json.dumps(state.get('repair_history', []), indent=2)}\n"
        f"TEST_REPORT: {state.get('test_report')}\n"
        f"GENERATED_CODE:\n{code_context[:5000]}\n" # Limit context
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Analyze this gem history:\n\n{context}")]
    response = cost_aware_invoke(messages)
    
    stats = parse_and_log_weaver_output(response.content, gem_id)
    print(f"   → Weaver complete: {stats['lessons_count']} lessons, {stats['taste_updates_count']} taste updates.")

    # Stamp final cost into PipelineState so checkpointed state is accurate.
    from tools.cost_tracker import cost_tracker
    return {
        "total_cost": cost_tracker.total_cost,
        "total_tokens": cost_tracker.total_tokens,
        "progress_log": [f"🕸️ Weaver Reflector: {stats['lessons_count']} lessons captured"],
    }


def _build_pipeline():
    """Build and return the compiled LangGraph pipeline. Called once at entry-point startup."""
    workflow = StateGraph(PipelineState)

    nodes = [
        ("document_auditor", document_auditor_node),
        ("vision_polisher", vision_polisher_node),
        ("human_review", human_review_node),
        ("ruthless_interrogator", ruthless_interrogator_node),
        ("bootstrapper", bootstrapper_node),
        ("uiux", uiux_node),
        ("architecture", architecture_node),
        ("business_strategist", business_strategist_node),
        ("landing_page", landing_page_node),
        ("platform_decision", platform_decision_node),
        ("code_orchestrator", code_orchestrator_node),
        ("frontend", frontend_node),
        ("backend", backend_node),
        ("data", data_node),
        ("qa_generator", qa_generator_node),
        ("qa", qa_node),
        ("repair", repair_node),
        ("director", director_node),
        ("infra", infra_node),
        ("cicd", cicd_node),
        ("sre", sre_node),
        ("deploy", deploy_node),
        ("git_publish", git_publish_node),
        ("shipping", shipping_node),
        ("weaver", weaver_node),
    ]
    for name, func in nodes:
        workflow.add_node(name, func)

    workflow.set_entry_point("document_auditor")
    workflow.add_edge("document_auditor", "vision_polisher")
    workflow.add_edge("vision_polisher", "human_review")

    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        {"ruthless_interrogator": "ruthless_interrogator", "vision_polisher": "vision_polisher"},
    )

    workflow.add_edge("ruthless_interrogator", "bootstrapper")
    workflow.add_edge("bootstrapper", "uiux")
    workflow.add_edge("uiux", "architecture")
    workflow.add_edge("architecture", "business_strategist")
    workflow.add_edge("business_strategist", "landing_page")
    workflow.add_edge("landing_page", "platform_decision")
    workflow.add_edge("platform_decision", "code_orchestrator")

    # Fan-out: code_orchestrator → frontend + backend + data (parallel)
    workflow.add_edge("code_orchestrator", "frontend")
    workflow.add_edge("code_orchestrator", "backend")
    workflow.add_edge("code_orchestrator", "data")

    # Fan-in: all three → qa_generator
    workflow.add_edge(["frontend", "backend", "data"], "qa_generator")
    workflow.add_edge("qa_generator", "qa")

    workflow.add_conditional_edges(
        "qa",
        route_after_qa,
        {"director": "director", "repair": "repair"},
    )
    workflow.add_edge("repair", "qa")

    workflow.add_conditional_edges(
        "director",
        lambda s: "infra" if s.get("director_approved", False) else "human_review",
        {"human_review": "human_review", "infra": "infra"},
    )

    workflow.add_edge("infra", "cicd")
    workflow.add_edge("cicd", "sre")
    workflow.add_edge("sre", "deploy")
    workflow.add_edge("deploy", "git_publish")
    workflow.add_conditional_edges(
        "git_publish",
        route_after_git_publish,
        {"shipping": "shipping", "end": END},
    )
    workflow.add_edge("shipping", "weaver")
    workflow.add_edge("weaver", END)

    _db_path = Path(__file__).resolve().parent / "checkpoints.db"
    conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    memory = SqliteSaver(conn)
    app = workflow.compile(checkpointer=memory)
    print("✅ PIPELINE READY — GemForge multi-agent factory compiled.")
    return app


_pipeline_app = None


def get_pipeline_app():
    """Lazily compile the LangGraph pipeline on first call.

    Callers that only need routing helpers, cost tracking, or other utilities
    pay zero graph-compilation cost.  Only the actual forge / resume paths
    trigger the SQLite + LangGraph build.
    """
    global _pipeline_app
    if _pipeline_app is None:
        _pipeline_app = _build_pipeline()
    return _pipeline_app
