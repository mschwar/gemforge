import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.memory.retriever import semantic_retriever
from core.build.cache import build_cache

class ConceptSeeder:
    """Seeds new projects using high-confidence semantic hits from the global cache."""
    
    def __init__(self, projects_root: Path):
        self.projects_root = projects_root

    def seed_from_memory(self, idea: str, target_repo_path: Path) -> List[str]:
        """
        Search memory for very similar projects. 
        If a hit is > 0.9 similarity, try to seed initial files.
        """
        print(f"   🔍 [SEEDER] Checking global memory for similar concepts to: '{idea[:40]}...'")
        
        # 1. Search for similar historical code/specs
        hits = semantic_retriever.search(idea, k=5)
        if not hits:
            return []

        seeded_files = []
        # Filter for high-confidence hits from different runs
        for hit in hits:
            # Distance in Chroma is usually L2 (lower is closer). 0.0 is exact match.
            # Assuming threshold 0.4 for a 'strong' hit for this model.
            if hit.get("distance", 1.0) > 0.4:
                continue
                
            source_project = hit["metadata"].get("project_name")
            source_doc_type = hit["metadata"].get("doc_type")
            
            if source_doc_type == "spec":
                print(f"   🌱 [SEEDER] Found strong concept match in project: {source_project}")
                # Future: Actually copy the file or use it as few-shot context
                # For now, we'll just log the discovery.
                
        return seeded_files

# Singleton placeholder (initialized in pipeline)
concept_seeder = None
