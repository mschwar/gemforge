"""
GemForge — Cost & Rate-Limit Awareness (Module 5)
Tracks Anthropic tokens + estimated $ cost per call. Stores in state + checkpoints.
"""
from datetime import datetime
from typing import Dict

class CostTracker:
    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0
        self.calls = 0

    def track_call(self, response) -> Dict:
        """Extract usage from Anthropic response and update totals."""
        if hasattr(response, "usage"):
            input_t = response.usage.input_tokens
            output_t = response.usage.output_tokens
            cost = (input_t * 0.000015 + output_t * 0.000075)  # Claude 3.5 Sonnet pricing
        else:
            input_t = output_t = cost = 0

        self.total_tokens += input_t + output_t
        self.total_cost += cost
        self.calls += 1

        return {
            "tokens": input_t + output_t,
            "cost": round(cost, 6),
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "calls": self.calls
        }

cost_tracker = CostTracker()
