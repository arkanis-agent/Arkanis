import re
import cache
import os
import requests
from typing import List, Dict, Tuple, Optional
from core.config_manager import config_manager
from core.logger import logger
from functools import wraps
from dataclasses import dataclass, field

@dataclass
class CacheKey:
    models_hash: str
    timestamp: int = field(default_factory=hash)

# Constants extracted for maintainability
class TaskConstants:
    """Centralized constants for task classification thresholds"""
    MAX_CONVERSATION_WORDS = 30
    MAX_SIMPLE_WORDS = 200
    MAX_MEDIUM_WORDS = 400
    MAX_COMPLEX_WORDS = 800
    MAX_CONTEXT_LENGTH = 4000
    MIN_MODEL_ID_LENGTH = 10
    CACHE_TTL_SECONDS = 300
    REQUEST_TIMEOUT = 5

class ModelStrategy:
    def __init__(self):
        # Compile regex patterns for performance (run once, use many)
        self.conversation_keywords = [
            re.compile(r'^(olá|ola|oi|tudo bem|bom dia|boa tarde|boa noite|teste|e ai|e aí|hey)\b'),
            re.compile(r'^(\?|!|valeu|obrigado|obrigada|show|top|entendi)\b'),
            re.compile(r'\b(como você está|quem é você|me ajude|socorro|qual seu nome|quem criou você)\b')
        ]

        self.simple_keywords = [
            re.compile(r'\b(traduza|traduzir|resuma|resumir|corrija|corrigir|formate|ortografia|leia|ler)\b')
        ]

        self.engineering_keywords = [
            re.compile(r'\b(landing\s*page|site|website|frontend|backend|react|vue|vite|css|tailwind|html|javascript|typescript|python|c\+\+|rust|golang|php|sql|api|rest|json|xml|yaml|docker|container|kubernetes)\b', re.IGNORECASE)
        ]
        
        self.complex_keywords = [
            re.compile(r'\b(arquitetura|analise|planejamento|codigo|código|sistema|debug|refatore|refatorar|documentacao|documentação|estrategia|estratégia|workflow|pipeline|auditoria|segurança)\b', re.IGNORECASE)
        ]
        
        self.CLOUD_TIERS: Dict[str, List[str]] = {
            "FREE": [],
            "LOW_COST": [
                "anthropic/claude-3-haiku",
                "anthropic/claude-3.5-haiku",
                "google/gemini-1.5-flash",
                "google/gemini-pro-1.5-8b",
                "openai/gpt-4o-mini",
                "openai/gpt-4o",
                "mistralai/mistral-small-24b-it-v1:free",
                "qwen/qwen-2-72b-instruct:free"
            ],
            "BALANCED": [
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3-sonnet",
                "google/gemini-1.5-pro",
                "openai/gpt-4-turbo",
                "deepseek/deepseek-chat",
                "meta-llama/llama-3.1-70b-instruct"
            ],
            "HIGH_PERFORMANCE": [
                "anthropic/claude-3.5-opus",
                "openai/o1-mini",
                "openai/o1-preview"
            ]
        }
        
        self._model_cache: Optional[Dict] = None
        self._cache_timestamp: float = 0

    def classify_task(self, user_input: str, context_length: int = 0) -> str:
        """Classifies task into categories with optimization."""
        if not user_input or not user_input.strip():
            return "conversation"
            
        input_lower: str = user_input.lower().strip()
        word_count: int = len(input_lower.split())

        # 1. Long context heuristic
        if word_count > TaskConstants.MAX_COMPLEX_WORDS or context_length > TaskConstants.MAX_CONTEXT_LENGTH:
            return "complex"

        # 2. Conversation check (highest priority for short inputs)
        if word_count < TaskConstants.MAX_CONVERSATION_WORDS:
            for pattern in self.conversation_keywords:
                if pattern.search(input_lower):
                    return "conversation"

        # 3. Engineering check
        for pattern in self.engineering_keywords:
            if pattern.search(input_lower):
                return "engineering"

        # 4. Complex task check
        for pattern in self.complex_keywords:
            if pattern.search(input_lower):
                return "complex"

        # 5. Simple utilities check
        if word_count < TaskConstants.MAX_SIMPLE_WORDS:
            for pattern in self.simple_keywords:
                if pattern.search(input_lower):
                    return "simple"

        # 6. Default fallback by word count
        if word_count < 20:
            return "conversation"
        elif 20 <= word_count <= TaskConstants.MAX_MEDIUM_WORDS:
            return "simple"
        elif TaskConstants.MAX_SIMPLE_WORDS < word_count <= TaskConstants.MAX_COMPLEX_WORDS:
            return "medium"
        else:
            return "complex"

    def _group_enabled_models(self, enabled_models: List[Dict]) -> Dict[str, List[str]]:
        """Caches model grouping with TTL and hash-based invalidation."""
        current_time: float = cache.current_time()
        models_key: str = str(sorted(m.get("id", "") for m in enabled_models))
        
        # Validate cache TTL
        if (self._model_cache and 
            self._cache_timestamp > (current_time - TaskConstants.CACHE_TTL_SECONDS) and
            self._model_cache.get('models_hash') == hash(models_key)):
            return self._model_cache.get('result', {})
            
        config = config_manager.load_config()
        tiers: Dict[str, List[str]] = {
            "FREE": [], "LOW_COST": [], "BALANCED": [], "HIGH_PERFORMANCE": []
        }
        
        for m in enabled_models:
            if not m.get("enabled", True):
                continue
            provider: str = m.get("provider", "openrouter").lower()
            if not config_manager.is_provider_ready(provider, config):
                continue
            mid: str = m["id"]
            
            # Check in predefined tiers first
            if mid in self.CLOUD_TIERS["HIGH_PERFORMANCE"]:
                tiers["HIGH_PERFORMANCE"].append(mid)
            elif mid in self.CLOUD_TIERS["BALANCED"]:
                tiers["BALANCED"].append(mid)
            elif mid in self.CLOUD_TIERS["LOW_COST"]:
                tiers["LOW_COST"].append(mid)
            elif provider in ["ollama", "lm_studio", "vllm"] or ":free" in mid.lower():
                tiers["FREE"].append(mid)
            else:
                tiers["BALANCED"].append(mid)
        
        # Store with TTL
        self._model_cache = {
            'models_hash': models_key,
            'result': tiers
        }
        self._cache_timestamp = current_time
        return tiers

    def get_fallback_chain(self, classification: str) -> List[str]:
        """Returns the fallback chain based on task classification."""
        chains: Dict[str, List[str]] = {
            "conversation": ["FREE", "LOW_COST", "BALANCED", "HIGH_PERFORMANCE"],
            "simple": ["LOW_COST", "FREE", "BALANCED", "HIGH_PERFORMANCE"],
            "medium": ["BALANCED", "HIGH_PERFORMANCE", "LOW_COST", "FREE"],
            "engineering": ["HIGH_PERFORMANCE", "BALANCED", "LOW_COST", "FREE"],
            "complex": ["HIGH_PERFORMANCE", "BALANCED", "LOW_COST", "FREE"]
        }
        return chains.get(classification, chains["complex"])

    def decide(self, user_input: str, system_prompt: str, enabled_models: List[Dict]) -> Tuple[str, str, str]:
        """Calculates best model with optimized fallback logic."""
        task_category: str = self.classify_task(user_input, len(system_prompt))
        grouped_tiers: Dict[str, List[str]] = self._group_enabled_models(enabled_models)
        fallback_chain: List[str] = self.get_fallback_chain(task_category)
        logger.info(f"Task classified as '{task_category.upper()}'. Chain: {' -> '.join(fallback_chain)}", symbol="⚖️")

        for tier in fallback_chain:
            models: List[str] = grouped_tiers.get(tier, [])
            if models:
                logger.info(f"Priority Model: {models[0]} ({tier})", symbol="🎯")
                return models[0], tier, task_category

        active_ids: List[str] = [m["id"] for m in enabled_models if m.get("enabled", True)]
        return (active_ids[0], "FALLBACK", "unknown") if active_ids else ("anthropic/claude-3-haiku", "FALLBACK", "unknown")

    def discover_best_provider(self) -> Tuple[Optional[str], Optional[str]]:
        """Zero-Touch Discovery: Provider detection with better error handling."""
        config = config_manager.load_config()
        providers = config.get("providers", {})

        try:
            # Priority 1: Ollama
            ollama_cfg = providers.get("ollama", {})
            if ollama_cfg.get("enabled", True):
                endpoint: str = ollama_cfg.get("endpoint", "http://localhost:11434/api/tags")
                res = requests.get(endpoint, timeout=TaskConstants.REQUEST_TIMEOUT)
                if res.status_code == 200:
                    models_data = res.json()
                    if models_data.get("models"):
                        return models_data["models"][0]["name"], "ollama"
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama discovery failed: {e}", symbol="⚠️")
        except Exception as e:
            logger.warning(f"Ollama discovery unexpected error: {e}", symbol="⚠️")

        # Priority 2: OpenRouter
        or_cfg = providers.get("openrouter", {})
        or_key: str = os.getenv("OPENROUTER_API_KEY") or or_cfg.get("api_key", "")
        if or_key and len(str(or_key).strip()) > TaskConstants.MIN_MODEL_ID_LENGTH:
            return "anthropic/claude-3-haiku", "openrouter"

        return None, None


# Singleton instance
strategy_engine: ModelStrategy = ModelStrategy()