from langgraph.types import interrupt
from state import PipelineState

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
