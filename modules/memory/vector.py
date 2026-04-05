import uuid
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from typing import Dict, Any, Optional
from core.logger import logger

class VectorMemory:
    """
    ARKANIS CHRONOS - Neural Hive (Vector Memory)
    Uses ChromaDB for semantic retrieval of past interactions and files.
    Allows ARKANIS to learn and recall context beyond the prompt window.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = Path(db_path) if db_path else Path(__file__).resolve().parent.parent.parent / "data" / "vector_db"
        self._db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=str(self._db_path))
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        
        self.interactions = self.client.get_or_create_collection(
            name="interactions",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )
        self.knowledge = self.client.get_or_create_collection(
            name="knowledge",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )

    def add_interaction(self, user_input: str, response: str, task_hint: str = "general") -> None:
        """Embeds and stores a full interaction cycle."""
        try:
            doc_id = f"int_{uuid.uuid4().hex[:8]}"
            content = f"USER: {user_input}\nARKANIS: {response}"
            self.interactions.add(
                documents=[content],
                metadatas=[{"type": "interaction", "task": task_hint}],
                ids=[doc_id]
            )
        except Exception as e:
            logger.error(f"Chronos Error (add_interaction): {e}")

    def add_knowledge(self, source: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Stores snippets of knowledge (files, documentation, etc)."""
        try:
            doc_id = f"knw_{uuid.uuid4().hex[:8]}"
            meta = (metadata or {}).copy()
            meta["source"] = source
            self.knowledge.add(
                documents=[content],
                metadatas=[meta],
                ids=[doc_id]
            )
        except Exception as e:
            logger.error(f"Chronos Error (add_knowledge): {e}")

    def query(self, query_text: str, n_results: int = 3, collection_type: str = "interactions") -> str:
        """Retrieves semantically relevant context for the current query."""
        try:
            collection = self.interactions if collection_type == "interactions" else self.knowledge
            results = collection.query(query_texts=[query_text], n_results=n_results)
            
            if not results or not results.get("documents") or not results["documents"][0]:
                return ""
                
            return "\n---\n".join(results["documents"][0])
        except Exception as e:
            logger.error(f"Chronos Error (query): {e}")
            return ""

_chronos_instance: Optional[VectorMemory] = None

def get_chronos_memory() -> VectorMemory:
    """Lazy singleton getter to prevent heavy DB initialization at import time."""
    global _chronos_instance
    if _chronos_instance is None:
        _chronos_instance = VectorMemory()
    return _chronos_instance
