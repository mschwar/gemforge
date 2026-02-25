from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timezone
import uuid

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:
    chromadb = None
    SentenceTransformer = None

from .semantic_index import semantic_indexer

class SemanticRetriever:
    def __init__(self, indexer=None):
        self.indexer = indexer or semantic_indexer
        self._model = None # Lazy load

    @property
    def model(self):
        if self._model is None and SentenceTransformer:
            # Using the same model as indexer
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        return self._model

    def search(self, query: str, k: int = 5, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for similar chunks in the semantic index."""
        if not self.indexer.collection or not self.model:
            return []

        # Generate embedding for the query
        query_embedding = self.model.encode(query).tolist()

        # Query ChromaDB
        results = self.indexer.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filters
        )

        # Parse and return the results
        formatted_results = []
        if results and results["documents"]:
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })
        
        return formatted_results

# Singleton
semantic_retriever = SemanticRetriever()
