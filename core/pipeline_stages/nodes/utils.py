import re
from pathlib import Path
from typing import Any
from core.runtime.sandbox import ProjectSandbox
from core.memory.semantic_index import semantic_indexer

def _index_files(run_id: str, project_name: str, paths: list[Path], doc_type: str = "source"):
    """Helper to index multiple files in the semantic memory."""
    for path in paths:
        try:
            semantic_indexer.index_file(run_id, project_name, path, doc_type)
        except Exception as e:
            print(f"   ⚠️ Semantic Indexing failed for {path.name}: {e}")

def parse_and_save_docs(content: str, sandbox: ProjectSandbox) -> tuple[dict[str, str], list[Path]]:
    """
    Parses a string containing multiple documents (separated by ===filename.md===)
    and saves them using the sandbox.
    """
    # Regex to find blocks like ===filename.md===
    pattern = r"===([^=\n]+?)===\n(.*?)(?=\n===|\Z)"
    matches = re.findall(pattern, content, re.DOTALL)
    
    saved_docs = {}
    saved_paths = []
    
    for filename, body in matches:
        filename = filename.strip()
        body = body.strip()
        try:
            p = sandbox.safe_write(filename, body)
            saved_docs[filename] = body[:200]
            saved_paths.append(p)
            print(f"   → Saved {filename}")
        except PermissionError:
            raise
        except Exception as e:
            print(f"   ⚠️ Failed to save {filename}: {e}")
            
    return saved_docs, saved_paths
