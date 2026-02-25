import os
from pathlib import Path
from state import PipelineState

def shipping_node(state: PipelineState):
    """26_shipping_manifest_agent.md — auto-generates launch metadata and checklists"""
    print("🚀 23. Shipping Manifest (v2.0) running...")
    from core.shipping.shipper import shipper as launch_shipper
    
    repo_path = state.get("repo_path")
    if not repo_path:
        return {"shipping_complete": False, "progress_log": ["⚠️ Shipping skipped (no repo)"]}
        
    vision = state.get("polished_vision", "")
    platform = state.get("selected_platform", "Web")
    
    strategy_path = Path(repo_path) / "BUSINESS_STRATEGY.md"
    strategy = ""
    if os.path.exists(strategy_path):
        with open(strategy_path) as f:
            strategy = f.read()
            
    launch_shipper.prepare_launch_manifest(repo_path, vision, strategy, platform)
    
    return {
        "shipping_complete": True,
        "progress_log": ["🚀 Launchpad: SHIPPING_MANIFEST.md ready"]
    }
