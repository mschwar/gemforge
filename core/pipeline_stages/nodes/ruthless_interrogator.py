from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from state import PipelineState

def ruthless_interrogator_node(state: PipelineState):
    print("🔨 2. Ruthless Interrogator generating canonical docs...")
    prompt = load_prompt("02_ruthless_interrogator.md")
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"""POLISHED_VISION:

{state['polished_vision']}

Generate all canonical docs now.""")
    ]
    response = cost_aware_invoke(messages)
    return {
        "canonical_docs": {"_raw_output": response.content},
        "progress_log": ["✅ Canonical docs generated"],
    }
