import os
import hashlib
import logging
import atexit
import uuid
import threading
from typing import Optional, Dict, Any, List

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    Settings = None

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    ARKANIS V3.1 - Semantic LLM Cache (Enhanced)
    Reduces latency and cost by using a vector database to store and retrieve similar LLM responses.
    """
    _MAX_CACHE_SIZE = 10000  # Maximum cache entries before triggering deletion
    _LOCK = threading.Lock()

    def __init__(self):
        self.enabled = False
        self.collection = None
        self._initialized = False
        self._init_lock = threading.Lock()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.persist_directory = os.path.join(self.base_dir, "data", "semantic_cache_db")
        
        os.makedirs(self.persist_directory, exist_ok=True)

    def _ensure_initialized(self):
        """Lazy initialization with double-checked locking pattern."""
        if not self._initialized and self.enabled:
            with self._init_lock:
                if not self._initialized:
                    try:
                        if not CHROMA_AVAILABLE:
                            logger.warning("ChromaDB not available, disabling cache")
                            self.enabled = False
                            return
                        
                        cache_disabled = os.getenv("ARKANIS_CACHE_DISABLED", "false").lower() == "false"
                        if not cache_disabled:
                            self.enabled = False
                            return
                        
                        self.client = chromadb.PersistentClient(
                            path=self.persist_directory,
                            settings=Settings(
                                anonymized_telemetry=False,
                                allow_reset=True
                            )
                        )
                        self.collection = self.client.get_or_create_collection(
                            name="llm_semantic_cache",
                            metadata={
                                "hnsw:space": "cosine",
                                "hnsw:construction_ef": 50,
                                "hnsw:search_ef": 50
                            }
                        )
                        self._register_shutdown_handler()
                        logger.info(f"🧠 Semantic Cache initialized at {self.persist_directory}")
                        self._initialized = True
                    except Exception as e:
                        logger.error(f"⚠️ Failed to initialize Semantic Cache: {str(e)}")
                        self.enabled = False
                        self._initialized = False

    def _register_shutdown_handler(self):
        """Registers cleanup handler for graceful shutdown."""
        if not hasattr(self, '_shutdown_registered'):
            def shutdown():
                try:
                    if hasattr(self, 'client') and self.client:
                        self.client.persist()
                    if hasattr(self, '_atexit_registered'):
                        atexit.unregister(shutdown)
                except Exception:
                    pass
            
            shutdown()
            setattr(self, '_shutdown_registered', True)

    def lookup(self, system_prompt: str, user_prompt: str, threshold: float = 0.95) -> Optional[str]:
        """
        Calculates semantic similarity and returns cached response if above threshold.
        Verifies system_prompt consistency to prevent identity leakage.
        """
        if not self.enabled or not user_prompt:
            return None
            
        self._ensure_initialized()
        if not self.collection:
            return None

        try:
            with self._LOCK:
                results = self.collection.query(
                    query_texts=[user_prompt],
                    n_results=1,
                    include=['documents', 'metadatas', 'distances']
                )
                
                if results and results['documents'] and isinstance(results['documents'][0], list) and len(results['documents'][0]) > 0:
                    distance = float(results['distances'][0][0])
                    similarity = 1 - distance

                    if similarity >= threshold:
                        current_system_hash = hashlib.sha256(system_prompt.encode('utf-8')).hexdigest()
                        cached_system_hash = results['metadatas'][0][0].get('system_hash', '')
                        
                        if cached_system_hash == current_system_hash:
                            return results['documents'][0][0]
            return None
        except Exception as e:
            logger.error(f"Semantic Cache Lookup Error: {str(e)}")
            return None

    def store(self, system_prompt: str, user_prompt: str, response: str):
        """Stores a response with consistent system identity hash."""
        if not self.enabled or not response:
            return

        self._ensure_initialized()
        if not self.collection:
            return

        try:
            with self._LOCK:
                system_hash = hashlib.sha256(system_prompt.encode('utf-8')).hexdigest()
                user_hash = hashlib.sha256(user_prompt.encode('utf-8')).hexdigest()
                doc_id = f"cache_{system_hash[:8]}_{user_hash[:8]}_{uuid.uuid4().shortuuid()}"
                size = self.collection.count()

                if size >= self._MAX_CACHE_SIZE - 1000:
                    self._compact_cache()

                self.collection.upsert(
                    ids=[doc_id],
                    documents=[response],
                    metadatas=[{
                        "system_hash": system_hash,
                        "user_prefix_hash": hashlib.sha256(user_prompt[:100].replace('\n', ' ').encode('utf-8')).hexdigest(),
                        "created_at": os.urandom(8).hex()
                    }]
                )
        except Exception as e:
            logger.error(f"Semantic Cache Store Error: {str(e)}")

    def _compact_cache(self):
        """Removes oldest entries when cache approaches maximum size."""
        try:
            with self._LOCK:
                current_size = self.collection.count()
                if current_size > self._MAX_CACHE_SIZE:
                    # Delete oldest entries by created_at timestamp
                    oldest_id = self.collection.get(
                        include=[],
                        limit=1,
                        order_by=[("created_at", "asc")]
                    )
                    
                    if oldest_id['ids']:
                        delete_id = oldest_id['ids'][0]
                        self.collection.delete(ids=[delete_id])
                        logger.debug(f"Cache compacted: removed entry {delete_id}")
        except Exception as e:
            logger.error(f"Cache compaction failed: {str(e)}")

    def clear(self):
        """Clears all cached intelligence safely."""
        if self.enabled and self.collection:
            try:
                with self._LOCK:
                    self.collection = self.client.get_or_create_collection("llm_semantic_cache")
                    self.collection.clear()
                    logger.info("Semantic Cache cleared successfully.")
            except Exception as e:
                logger.error(f"Failed to clear cache: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """Returns current cache status for monitoring."""
        self._ensure_initialized()
        size = self.collection.count() if self.collection else 0
        return {
            "enabled": self.enabled,
            "initialized": self._initialized,
            "current_size": size,
            "max_size": self._MAX_CACHE_SIZE,
            "persist_directory": self.persist_directory
        }


class SemanticCacheManager:
    """Singleton manager for SemanticCache instances."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = SemanticCache()
        return cls._instance


def get_semantic_cache() -> SemanticCache:
    """Returns the singleton instance safely."""
    return SemanticCacheManager()
