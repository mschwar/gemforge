import unittest
from core.repair.signature import build_failure_signature
from core.runtime.reducer import StateReducer

class TestBlueprint02Memory(unittest.TestCase):
    def test_failure_signature_extraction(self):
        """Verify signature builder correctly parses raw error logs."""
        raw_output = """
        Error: Module not found: Error: Can't resolve './components/Button' in '/app/src'
        at Object.<anonymous> (/app/src/index.tsx:5:1)
        """
        sig = build_failure_signature("nextjs", "jest", raw_output)
        self.assertIn("error=module-not-found", sig)
        self.assertIn("path=index.tsx", sig)
        self.assertIn("platform=nextjs", sig)

        raw_output_2 = "TypeError: Cannot read property 'map' of undefined"
        sig_2 = build_failure_signature("web", "jest", raw_output_2)
        self.assertIn("error=type-error", sig_2)

    def test_state_reducer(self):
        """Verify the reducer correctly rehydrates state from a sequence of events."""
        reducer = StateReducer()
        events = [
            {
                "run_id": "run-1",
                "step_id": "step-1",
                "event_type": "step.completed",
                "payload": {
                    "state_patch": {"key1": "val1", "progress_log": ["started"]},
                    "metrics": {"tokens_used": 100, "cost_usd": 0.01}
                }
            },
            {
                "run_id": "run-1",
                "step_id": "step-2",
                "event_type": "step.completed",
                "payload": {
                    "state_patch": {"key2": "val2", "progress_log": ["middle"]},
                    "metrics": {"tokens_used": 200, "cost_usd": 0.02}
                }
            }
        ]
        
        final_state = reducer.reduce(events)
        self.assertEqual(final_state["key1"], "val1")
        self.assertEqual(final_state["key2"], "val2")
        self.assertEqual(final_state["total_tokens"], 300)
        self.assertEqual(final_state["total_cost"], 0.03)
        self.assertEqual(len(final_state["progress_log"]), 2)

if __name__ == "__main__":
    unittest.main()
