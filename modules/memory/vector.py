import os
import uuid
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional, Union, Literal
from pathlib import Path
from core.logger import logger

class VectorMemory:
    """
    ARKANIS CHRONOS - Neural Hive (Vector Memory)
    Uses ChromaDB for semantic retrieval of past interactions and files.
    Allows ARKANIS to learn and recall context beyond the prompt window.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        base_path = Path(__file__).resolve().parent.parent.parent
        self.db_path = Path(db_path) if db_path else base_path / "data" / "vector_db"
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=str(self.db_path))
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
            doc_id = f"int_{uuid.uuid4().hex}"
            content = f"USUÁRIO: {user_input}\nARKANIS: {response}"
            self.interactions.add(
                documents=[content],
                metadatas=[{"type": "interaction", "task": task_hint}],
                ids=[doc_id]
            )
        except Exception as e:
            logger.error(f"Chronos Error (add): {e}")

    def add_knowledge(self, source: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Stores snippets of knowledge (files, documentation, etc)."""
        try:
            doc_id = f"knw_{uuid.uuid4().hex}"
            meta = {"source": source, **(metadata or {})}
            self.knowledge.add(
                documents=[content],
                metadatas=[meta],
                ids=[doc_id]
            )
        except Exception as e:
            logger.error(f"Chronos Error (knowledge): {e}")

    def query(self, query_text: str, n_results: int = 3, collection_type: Literal["interactions", "knowledge"] = "interactions") -> str:
        """Retrieves semantically relevant context for the current query."""
        try:
            collection = self.interactions if collection_type == "interactions" else self.knowledge
            results = collection.query(query_texts=[query_text], n_results=n_results)
            
            documents = results.get("documents", [])
            if not documents or len(documents) == 0 or not documents[0]:
                return ""
                
            return "\n---\n".join(documents[0])
            
        except Exception as e:
            logger.error(f"Chronos Error (query): {e}")
            return ""

# Global singleton
chronos_memory = VectorMemory()