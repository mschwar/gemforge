"""
GemForge — Shared LLM helpers.

Thin module that holds the LLM client and cost-aware invoke wrapper.
Importing this has zero side effects — no graph construction, no SQLite,
no git commits. All core/ modules should import from here instead of
from pipeline.py to avoid the circular dependency.
"""
from langchain_anthropic import ChatAnthropic

from core.evolution.prompt_loader import prompt_loader
from tools.cost_tracker import cost_tracker

_llm: ChatAnthropic | None = None


def get_llm() -> ChatAnthropic:
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)
    return _llm


def cost_aware_invoke(prompt_messages):
    """Invoke the LLM and track token usage and cost."""
    response = get_llm().invoke(prompt_messages)
    cost_tracker.track_call(response)
    return response


def load_prompt(agent_id: str) -> str:
    """Load the active prompt for an agent (with taste injection)."""
    return prompt_loader.load_active_prompt(agent_id.replace(".md", ""))
