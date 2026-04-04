import os
import hashlib
import logging
from typing import Optional

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

logger = logging.getLogger("uvicorn")

class SemanticCache:
    """
    ARKANIS V3.1 - Semantic LLM Cache
    Reduces latency and cost by using a vector database to store and retrieve similar LLM responses.
    """
    def __init__(self):
        self.enabled = CHROMA_AVAILABLE and os.getenv("ARKANIS_CACHE_DISABLED", "false").lower() == "false"
        self.collection = None
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.persist_directory = os.path.join(self.base_dir, "data", "semantic_cache_db")
        
        if self.enabled:
            try:
                self.client = chromadb.PersistentClient(path=self.persist_directory)
                # Note: ChromaDB will automatically handle embedding function (default: all-MiniLM-L6-v2)
                self.collection = self.client.get_or_create_collection(
                    name="llm_semantic_cache",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"🧠 Semantic Cache initialized at {self.persist_directory}")
            except Exception as e:
                logger.error(f"⚠️ Failed to initialize Semantic Cache: {str(e)}")
                self.enabled = False

    def lookup(self, system_prompt: str, user_prompt: str, threshold: float = 0.95) -> Optional[str]:
        """
        Calculates semantic similarity and returns cached response if above threshold.
        Also verifies if the system_prompt (personality/identity) is consistent.
        """
        if not self.enabled or not self.collection or not user_prompt:
            return None
            
        try:
            # Query the collection for similarity
            results = self.collection.query(
                query_texts=[user_prompt],
                n_results=1,
                include=['documents', 'metadatas', 'distances']
            )
            
            if results and results['documents'] and results['documents'][0]:
                distance = results['distances'][0][0]
                similarity = 1 - distance # Cosine similarity
                
                if similarity >= threshold:
                    # Check if identity (system_prompt) matches to avoid leaked personality traits
                    current_system_hash = hashlib.sha256(system_prompt.encode('utf-8')).hexdigest()
                    cached_system_hash = results['metadatas'][0][0].get('system_hash')
                    
                    if cached_system_hash == current_system_hash:
                        return results['documents'][0][0]
            
            return None
        except Exception as e:
            logger.error(f"Semantic Cache Lookup Error: {str(e)}")
            return None

    def store(self, system_prompt: str, user_prompt: str, response: str):
        """Stores a response with its system_prompt signature."""
        if not self.enabled or not self.collection or not response:
            return
            
        try:
            system_hash = hashlib.sha256(system_prompt.encode('utf-8')).hexdigest()
            doc_id = f"cache_{hashlib.md5(user_prompt.encode()).hexdigest()}"
            
            self.collection.upsert(
                ids=[doc_id],
                documents=[response],
                metadatas=[{
                    "system_hash": system_hash,
                    "user_brief": user_prompt[:100]
                }]
            )
        except Exception as e:
            logger.error(f"Semantic Cache Store Error: {str(e)}")

    def clear(self):
        """Clears all cached intelligence."""
        if self.enabled and self.client:
            try:
                self.client.delete_collection("llm_semantic_cache")
                self.collection = self.client.get_or_create_collection(name="llm_semantic_cache")
                logger.info("Semantic Cache cleared.")
            except Exception as e:
                logger.error(f"Failed to clear cache: {str(e)}")

# Singleton Instance
semantic_cache = SemanticCache()
