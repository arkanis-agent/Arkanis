import re
from typing import List, Dict, Tuple, Optional
from core.config_manager import config_manager
from core.logger import logger

class ModelStrategy:
    """
    ARKANIS V3: Cost-Aware Auto Strategy Engine
    Dynamically orchestrates fallback tiers to save costs.
    Prioritizes FREE local models for basic chat and API/High Performance 
    for complex engineering tasks.
    """

    def __init__(self):
        # Conversational tasks (basic chat without heavy lifting)
        self.conversation_keywords = [
            r'^(olá|ola|oi|tudo bem|bom dia|boa tarde|boa noite|teste|e ai|e aí|hey)\b',
            r'^(\?|!|valeu|obrigado|obrigada|show|top|entendi)\b',
            r'\b(como você está|quem é você|me ajude|socorro|qual seu nome|quem criou você)\b'
        ]

        # Simple utility tasks
        self.simple_keywords = [
            r'\b(traduza|traduzir|resuma|resumir|corrija|corrigir|formate|ortografia|leia|ler)\b'
        ]

        # Engineering/Coding specific tasks
        self.engineering_keywords = [
            r'\b(landing\s*page|site|website|frontend|backend|react|vue|vite|css|tailwind|html|javascript|typescript|python|c\+\+|rust|golang|php|sql|api|rest|json|xml|yaml|docker|container|kubernetes)\b',
            r'\b(projeto|app|aplicativo|software|dev|desenvolva|crie um script|automatize|automacao|automação|faça|fazer|construa|monte|programe|codifique|implemente|execute)\b'
        ]
        
        # Deep engineering/reasoning
        self.complex_keywords = [
            r'\b(arquitetura|analise|planejamento|codigo|código|sistema|debug|refatore|refatorar|documentacao|documentação|estrategia|estratégia|workflow|pipeline|auditoria|segurança)\b'
        ]

        # Hardcoded premium mappings for cloud models
        # Local ones (Ollama, LM_Studio) will be automatically grouped as FREE.
        self.CLOUD_TIERS = {
            "LOW COST": [
                "anthropic/claude-3-haiku",
                "anthropic/claude-3.5-haiku",
                "google/gemini-2.5-flash",
                "google/gemini-2.8-flash",
                "google/gemini-1.5-flash",
                "google/gemini-pro-1.5-8b",
                "openai/gpt-4o-mini",
                "mistralai/mistral-small-24b-it-v1:free",
                "qwen/qwen-2-72b-instruct:free",
                "minimax-m2.5",
                "glm-4"
            ],
            "BALANCED": [
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3-sonnet",
                "claude-3-5-sonnet-latest",
                "google/gemini-2.5-pro",
                "google/gemini-3.0-pro",
                "gemini-2.5-pro",
                "openai/gpt-4o",
                "openai/gpt-4-turbo",
                "deepseek/deepseek-chat",
                "meta-llama/llama-3.1-405b-instruct",
                "grok-beta",
                "mistral-large-latest",
                "venice-pro"
            ],
            "HIGH PERFORMANCE": [
                "anthropic/claude-3.5-opus",
                "anthropic/claude-3-opus",
                "claude-3-opus-latest",
                "openai/o1-preview",
                "openai/o1-mini",
                "openai/o3-mini",
                "x-ai/grok-2",
                "google/gemini-2.0-pro-exp",
                "qwen/qwen3.6-plus:free"
            ]
        }

    def classify_task(self, user_input: str, context_length: int = 0) -> str:
        """
        Classifies task into: 'conversation', 'simple', 'medium', or 'complex'.
        """
        input_lower = user_input.lower().strip()
        word_count = len(input_lower.split())

        # 1. Very long context or huge prompt -> complex
        if word_count > 800 or context_length > 4000:
            return "complex"

        # 2. Check for simple conversations/greetings
        for pattern in self.conversation_keywords:
            if re.search(pattern, input_lower) and word_count < 30:
                return "conversation"

        # 3. Check for specialized engineering/coding
        for pattern in self.engineering_keywords:
            if re.search(pattern, input_lower):
                return "engineering"

        # 4. Check for complex architecture/reasoning
        for pattern in self.complex_keywords:
            if re.search(pattern, input_lower):
                return "complex"

        # 5. Check for simple utilities
        for pattern in self.simple_keywords:
            if re.search(pattern, input_lower) and word_count < 200:
                return "simple"

        # 5. Default heuristic fallback
        if word_count < 20:
            return "conversation"
        elif 20 <= word_count <= 60:
            return "simple"
        elif 60 < word_count <= 400:
            return "medium"
        else:
            return "complex"

    def _group_enabled_models(self, enabled_models: List[Dict]) -> Dict[str, List[str]]:
        """Splits models into their respective cost tiers, respecting provider readiness."""
        config = config_manager.load_config()
        tiers = {
            "FREE": [],
            "LOW COST": [],
            "BALANCED": [],
            "HIGH PERFORMANCE": []
        }
        for m in enabled_models:
            if not m.get("enabled", True):
                continue
            
            provider = m.get("provider", "openrouter")
            if not config_manager.is_provider_ready(provider, config):
                continue
                
            mid = m["id"]
            
            if provider in ["ollama", "lm_studio", "vllm"] or ":free" in mid.lower():
                tiers["FREE"].append(mid)
            elif mid in self.CLOUD_TIERS["HIGH PERFORMANCE"]:
                tiers["HIGH PERFORMANCE"].append(mid)
            elif mid in self.CLOUD_TIERS["BALANCED"]:
                tiers["BALANCED"].append(mid)
            elif mid in self.CLOUD_TIERS["LOW COST"]:
                tiers["LOW COST"].append(mid)
            else:
                # If unmapped cloud model, assume balanced for safety
                tiers["BALANCED"].append(mid)
                
        return tiers

    def get_fallback_chain(self, classification: str) -> List[str]:
        """Returns the fallback chain (tiers to try in order) based on task."""
        if classification == "conversation":
            return ["FREE", "LOW COST", "BALANCED", "HIGH PERFORMANCE"]
        elif classification == "simple":
            return ["LOW COST", "FREE", "BALANCED", "HIGH PERFORMANCE"]
        elif classification == "medium":
            return ["BALANCED", "HIGH PERFORMANCE", "LOW COST", "FREE"]
        elif classification == "engineering":
            # Engineering tasks DEMAND high performance or balanced coding models
            return ["HIGH PERFORMANCE", "BALANCED", "LOW COST", "FREE"]
        else: # complex
            return ["HIGH PERFORMANCE", "BALANCED", "LOW COST", "FREE"]

    def decide(self, user_input: str, system_prompt: str, enabled_models: List[Dict]) -> Tuple[str, str, str]:
        """
        Calculates the best possible model prioritizing cost efficiency.
        Returns: (model_id, cost_tier_name, task_category)
        """
        task_category = self.classify_task(user_input, len(system_prompt))
        grouped_tiers = self._group_enabled_models(enabled_models)
        
        fallback_chain = self.get_fallback_chain(task_category)
        logger.info(f"Task classified as '{task_category.upper()}'. Selecting fallback chain: {' -> '.join(fallback_chain)}", symbol="⚖️")

        for tier in fallback_chain:
            models_in_tier = grouped_tiers[tier]
            if len(models_in_tier) > 0:
                logger.info(f"Priority Model: {models_in_tier[0]} ({tier})", symbol="🎯")
                return models_in_tier[0], tier, task_category

        # Absolute Failsafe (should theoretically never happen if any model is on)
        active_ids = [m["id"] for m in enabled_models if m.get("enabled", True)]
        fallback_id = active_ids[0] if active_ids else "anthropic/claude-3-haiku"
        return fallback_id, "FALLBACK", "unknown"

    def discover_best_provider(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Zero-Touch Discovery: Detects the best available provider and model.
        Returns: (model_id, provider_id)
        """
        import os
        import requests

        config = config_manager.load_config()
        providers = config.get("providers", {})

        # Priority 1: Ollama (Local)
        ollama_cfg = providers.get("ollama", {})
        if ollama_cfg.get("enabled", True):
            endpoint = ollama_cfg.get("endpoint", "http://localhost:11434/api/tags")
            # Convert /api/chat to /api/tags for model listing if needed
            tags_url = endpoint.replace("/api/chat", "/api/tags")
            try:
                # 1. Is service running?
                res = requests.get(tags_url, timeout=2)
                if res.status_code == 200:
                    models_data = res.json()
                    models = models_data.get("models", [])
                    if models:
                        # Success! Use the first local model found
                        return models[0]["name"], "ollama"
            except Exception:
                pass

        # Priority 2: OpenRouter (Cloud)
        or_cfg = providers.get("openrouter", {})
        # We check both the config and the environment for the key
        or_key = os.getenv("OPENROUTER_API_KEY") or or_cfg.get("api_key")
        if or_key and len(or_key.strip()) > 10:
            # Fallback to a safe, reliable cloud default
            return "anthropic/claude-3-haiku", "openrouter"

        # Final Fallback / Setup Required
        return None, None

# Singleton instance
strategy_engine = ModelStrategy()
