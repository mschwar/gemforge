from typing import Dict, List, Set

# Static map of node dependencies
# Key: node_id, Value: List of node_ids that this node depends on
DEPENDENCY_MAP: Dict[str, List[str]] = {
    "document_auditor": [],
    "vision_polisher": ["document_auditor"],
    "human_review": ["vision_polisher"],
    "ruthless_interrogator": ["human_review"],
    "bootstrapper": ["ruthless_interrogator"],
    "uiux": ["bootstrapper"],
    "architecture": ["uiux"],
    "business_strategist": ["bootstrapper"],
    "landing_page": ["business_strategist"],
    "platform_decision": ["architecture", "landing_page"],
    "code_orchestrator": ["platform_decision", "uiux", "architecture"],
    "frontend": ["code_orchestrator", "uiux", "architecture"],
    "backend": ["code_orchestrator", "uiux", "architecture"],
    "data": ["code_orchestrator", "uiux", "architecture"],
    "qa_generator": ["frontend", "backend", "data"],
    "qa": ["qa_generator"],
    "repair": ["qa"],
    "director": ["qa", "repair", "frontend", "backend", "data"],
    "infra": ["director"],
    "cicd": ["infra"],
    "sre": ["cicd"],
    "deploy": ["sre"],
    "git_publish": ["deploy"],
    "shipping": ["git_publish"],
    "weaver": ["shipping"]
}

def get_downstream_nodes(node_id: str) -> Set[str]:
    """Returns all nodes that directly or indirectly depend on the given node."""
    downstream = set()
    
    def find_recursive(current_id: str):
        for candidate_id, deps in DEPENDENCY_MAP.items():
            if current_id in deps and candidate_id not in downstream:
                downstream.add(candidate_id)
                find_recursive(candidate_id)
                
    find_recursive(node_id)
    return downstream

def get_upstream_nodes(node_id: str) -> Set[str]:
    """Returns all nodes that the given node directly or indirectly depends on."""
    upstream = set()
    
    def find_recursive(current_id: str):
        deps = DEPENDENCY_MAP.get(current_id, [])
        for dep in deps:
            if dep not in upstream:
                upstream.add(dep)
                find_recursive(dep)
                
    find_recursive(node_id)
    return upstream
