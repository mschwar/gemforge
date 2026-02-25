import os
import json
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from state import PipelineState

def weaver_node(state: PipelineState):
    """21_weaver_reflector.md — extracts lessons & updates user taste"""
    print("🕸️  22. Weaver Reflector (v2.0) running...")
    from core.evolution.iterator import IterationEngine
    from core.evolution.weaver import parse_and_log_weaver_output
    from core.swarm.swarm_factory import swarm_factory
    
    prompt = load_prompt("21_weaver_reflector.md")
    gem_id = state.get("raw_idea", "Unknown")[:30]
    
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
        f"GENERATED_CODE:\n{code_context[:5000]}\n"
    )
    
    messages = [SystemMessage(content=prompt), HumanMessage(content=f"Analyze this gem history:\n\n{context}")]
    response = cost_aware_invoke(messages)
    
    stats = parse_and_log_weaver_output(response.content, gem_id)
    print(f"   → Weaver complete: {stats['lessons_count']} lessons, {stats['taste_updates_count']} taste updates.")

    swarm_factory.cleanup_temp_agents()

    from tools.cost_tracker import cost_tracker
    return {
        "total_cost": cost_tracker.total_cost,
        "total_tokens": cost_tracker.total_tokens,
        "progress_log": [f"🕸️ Weaver Reflector: {stats['lessons_count']} lessons captured"],
    }
