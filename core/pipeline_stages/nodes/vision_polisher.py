from langchain_core.messages import HumanMessage, SystemMessage
from core.llm import cost_aware_invoke, load_prompt
from state import PipelineState

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
