import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
except ImportError:
    # Allow implementation even if libs are not yet installed in the current environment
    chromadb = None
    SentenceTransformer = None

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_DIR = _REPO_ROOT / "memory" / "semantic"
_DB_DIR.mkdir(parents=True, exist_ok=True)

class SemanticIndexer:
    def __init__(self, db_path: str = None, collection_name: str = "gemforge_chunks"):
        self.sqlite_path = db_path or str(_DB_DIR / "semantic_metadata.db")
        self.chroma_path = str(_DB_DIR / "chroma_db")
        self.collection_name = collection_name
        
        self._init_sqlite()
        self._init_chroma()
        self._model = None # Lazy load

    @property
    def model(self):
        if self._model is None and SentenceTransformer:
            # Using a small, fast model for local execution
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def _init_sqlite(self):
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_docs (
                    doc_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text_excerpt TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    vector_ref TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def _init_chroma(self):
        if chromadb:
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        else:
            self.client = None
            self.collection = None

    def index_file(self, run_id: str, project_name: str, file_path: Path, doc_type: str = "source"):
        """Chunk a file and index it in both SQLite and Chroma."""
        if not file_path.exists():
            return
            
        content = file_path.read_text(errors="ignore")
        if not content.strip():
            return
            
        doc_id = str(uuid.uuid4())
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Simple line-based chunking for Phase 0
        lines = content.splitlines()
        chunk_size = 50 # lines per chunk
        chunks = [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]
        
        doc_metadata = {
            "doc_id": doc_id,
            "run_id": run_id,
            "project_name": project_name,
            "path": str(file_path.relative_to(_REPO_ROOT) if _REPO_ROOT in file_path.parents else file_path),
            "doc_type": doc_type,
            "content_hash": content_hash,
            "chunk_count": len(chunks),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                "INSERT INTO semantic_docs (doc_id, run_id, project_name, path, doc_type, content_hash, chunk_count, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (doc_id, run_id, project_name, doc_metadata["path"], doc_type, content_hash, len(chunks), doc_metadata["created_at"])
            )
            
            for i, chunk_lines in enumerate(chunks):
                chunk_text = "\n".join(chunk_lines)
                chunk_id = f"{doc_id}_{i}"
                
                # Generate embedding
                embedding = []
                if self.model:
                    embedding = self.model.encode(chunk_text).tolist()
                
                # Store in Chroma
                if self.collection:
                    self.collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding] if embedding else None,
                        documents=[chunk_text],
                        metadatas=[{
                            "doc_id": doc_id,
                            "run_id": run_id,
                            "project_name": project_name,
                            "chunk_index": i,
                            "doc_type": doc_type
                        }]
                    )
                
                # Store in SQLite
                conn.execute(
                    "INSERT INTO semantic_chunks (chunk_id, doc_id, run_id, chunk_index, text_excerpt, token_count, vector_ref, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (chunk_id, doc_id, run_id, i, chunk_text[:200], len(chunk_text.split()), chunk_id, doc_metadata["created_at"])
                )
            conn.commit()
        
        return doc_id

# Singleton
semantic_indexer = SemanticIndexer()
