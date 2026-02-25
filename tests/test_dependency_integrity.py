import unittest
from core.build.graph import DEPENDENCY_MAP
from pipeline import _build_pipeline

class TestDependencyIntegrity(unittest.TestCase):
    def test_dependency_map_matches_graph_nodes(self):
        """Verify that every node in the graph is accounted for in the DEPENDENCY_MAP."""
        app = _build_pipeline()
        graph_nodes = set(app.nodes.keys())
        map_nodes = set(DEPENDENCY_MAP.keys())
        
        # Exclude internal LangGraph nodes like __start__ and __end__
        internal_nodes = {"__start__", "__end__"}
        actual_graph_nodes = graph_nodes - internal_nodes
        
        missing_in_map = actual_graph_nodes - map_nodes
        extra_in_map = map_nodes - actual_graph_nodes
        
        self.assertEqual(len(missing_in_map), 0, f"Nodes in graph but missing from DEPENDENCY_MAP: {missing_in_map}")
        self.assertEqual(len(extra_in_map), 0, f"Nodes in DEPENDENCY_MAP but missing from graph: {extra_in_map}")

    def test_no_circular_dependencies(self):
        """Verify that the dependency map does not contain cycles."""
        visited = set()
        path = set()

        def has_cycle(node_id):
            visited.add(node_id)
            path.add(node_id)
            for neighbor in DEPENDENCY_MAP.get(node_id, []):
                if neighbor in path:
                    return True
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
            path.remove(node_id)
            return False

        for node in DEPENDENCY_MAP:
            if node not in visited:
                self.assertFalse(has_cycle(node), f"Circular dependency detected starting at node: {node}")

if __name__ == "__main__":
    unittest.main()
