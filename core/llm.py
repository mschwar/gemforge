"""
GemForge — Shared LLM helpers.

Thin module that holds the LLM client and cost-aware invoke wrapper.
Importing this has zero side effects — no graph construction, no SQLite,
no git commits. All core/ modules should import from here instead of
from pipeline.py to avoid the circular dependency.
"""
import os
import time

from langchain_anthropic import ChatAnthropic

from core.evolution.prompt_loader import prompt_loader
from tools.cost_tracker import cost_tracker

_llm: ChatAnthropic | None = None
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504, 529}


def get_llm() -> ChatAnthropic:
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)
    return _llm


def _is_retryable_llm_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in _RETRYABLE_STATUS_CODES:
        return True

    message = str(exc).lower()
    error_name = type(exc).__name__.lower()
    retry_markers = (
        "overloaded",
        "rate limit",
        "too many requests",
        "temporar",
        "timeout",
        "connection reset",
        "service unavailable",
    )
    return any(marker in message for marker in retry_markers) or "timeout" in error_name


def cost_aware_invoke(prompt_messages):
    """Invoke the LLM and track token usage and cost."""
    max_attempts = max(1, int(os.getenv("GEMFORGE_LLM_MAX_ATTEMPTS", "3")))
    base_delay = max(0.1, float(os.getenv("GEMFORGE_LLM_RETRY_BASE_SECONDS", "1.5")))

    for attempt in range(1, max_attempts + 1):
        try:
            response = get_llm().invoke(prompt_messages)
            cost_tracker.track_call(response)
            return response
        except Exception as exc:
            if attempt >= max_attempts or not _is_retryable_llm_error(exc):
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), 12.0)
            print(
                f"   ⚠️ LLM transient error ({type(exc).__name__}); "
                f"retrying in {delay:.1f}s ({attempt}/{max_attempts})"
            )
            time.sleep(delay)


def load_prompt(agent_id: str) -> str:
    """Load the active prompt for an agent (with taste injection)."""
    return prompt_loader.load_active_prompt(agent_id.replace(".md", ""))
