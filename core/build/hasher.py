import hashlib
import os
from pathlib import Path
from typing import List, Optional, Set

def calculate_string_hash(content: str) -> str:
    """Returns SHA-256 hash of a string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def calculate_file_hash(file_path: Path) -> str:
    """Returns SHA-256 hash of a file's content."""
    if not file_path.exists():
        return ""
    
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def calculate_dir_hash(dir_path: Path, exclude_patterns: Optional[Set[str]] = None) -> str:
    """
    Recursively calculates a hash for a directory's contents.
    
    Excludes files/folders matching exclude_patterns.
    Default exclusions: .git, node_modules, __pycache__, .DS_Store, BUILD_MANIFEST.json
    """
    if not dir_path.exists() or not dir_path.is_dir():
        return ""

    if exclude_patterns is None:
        exclude_patterns = {".git", "node_modules", "__pycache__", ".DS_Store", "BUILD_MANIFEST.json"}

    hashes = []
    
    # Walk the directory, sorting everything for determinism
    for root, dirs, files in os.walk(dir_path):
        # Filter directories in-place to prevent os.walk from entering them
        dirs[:] = [d for d in dirs if d not in exclude_patterns]
        
        rel_root = Path(root).relative_to(dir_path)
        
        for file in sorted(files):
            if file in exclude_patterns:
                continue
                
            file_path = Path(root) / file
            file_rel_path = rel_root / file
            
            file_hash = calculate_file_hash(file_path)
            # Incorporate both path and content into the cumulative hash
            hashes.append(f"{file_rel_path}:{file_hash}")

    # Combine all individual file hashes into one master hash
    combined = "|".join(sorted(hashes))
    return calculate_string_hash(combined)
