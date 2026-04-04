import os
import requests
import json
import time
from typing import Optional, List, Dict, Any
from core.config_manager import config_manager
from core.model_strategy import strategy_engine
from core.cost_governor import governor
from core.logger import logger
from core.semantic_cache import semantic_cache

class LLMRouter:
    """
    LLM ROUTER V3: Abstraction layer for multiple LLM providers.
    Dynamically loads configuration from providers.json.
    """

    def __init__(self):
        self._load_config()
        # 1. Start with configured model
        self.active_model = os.getenv("ARKANIS_MODEL")
        self.active_provider = self._get_provider_for_model(self.active_model) if self.active_model else None

        # 2. Zero-Touch Discovery if nothing is correctly configured
        if not self.active_model or not self.active_provider:
             self._discover()
        
        self.timeout = int(os.getenv("ARKANIS_TIMEOUT", 30))
        self.auto_strategy = True # Auto strategy toggle state (Default Active)
        self.active_tier = None # Caches the cost tier of the selected model

    def _discover(self):
        """Internal helper to find the best available model."""
        best_model, best_provider = strategy_engine.discover_best_provider()
        if best_model and best_provider:
            logger.info(f"Auto-Configuration identified optimal provider: {best_provider} -> {best_model}")
            self.active_model = best_model
            self.active_provider = best_provider
        else:
            # Absolute failsafe defaults if discovery fails (system will prompt setup in UI)
            self.active_model = "anthropic/claude-3-haiku"
            self.active_provider = "openrouter"

    def set_auto_strategy(self, state: bool):
        self.auto_strategy = state

    def _load_config(self):
        """Loads providers and models from config_manager."""
        config = config_manager.load_config()
        self.providers = config.get("providers", {})
        self.all_models = config.get("models", [])
        
        # Build categorized models for UI Compatibility
        self.MODELS = {"cloud": [], "local": []}
        for m in self.all_models:
            if not m.get("enabled", True):
                continue
                
            prov_id = m.get("provider", "openrouter")
            provider_cfg = self.providers.get(prov_id, {})
            
            # 1. Is the provider globally enabled and ready?
            if not config_manager.is_provider_ready(prov_id, config):
                continue

            category = "cloud" if prov_id not in ["ollama", "lm_studio", "vllm"] else "local"
            self.MODELS[category].append(m)

    def _get_provider_for_model(self, model_id: str) -> str:
        for m in self.all_models:
            if m["id"] == model_id:
                return m["provider"]
        return "openrouter" # Fallback

    def set_model(self, model_id: str) -> bool:
        """Dynamically switch the active model and provider."""
        # Refresh config in case it changed via UI
        self._load_config()

        for m in self.all_models:
            if m["id"] == model_id and m.get("enabled", True):
                # Extra check: is the provider actually ready?
                config = config_manager.load_config()
                if config_manager.is_provider_ready(m["provider"], config):
                    self.active_model = model_id
                    self.active_provider = m["provider"]
                    # Update active tier identification
                    tier = "UNKNOWN"
                    if m["provider"] in ["ollama", "lm_studio", "vllm"] or ":free" in model_id.lower():
                        tier = "FREE"
                    else:
                        for t_name, m_list in strategy_engine.CLOUD_TIERS.items():
                            if model_id in m_list:
                                tier = t_name
                                break
                    
                    self.active_tier = tier
                    logger.info(f"Roteador: Modelo definido para {model_id} (Tier: {tier})")
                    return True

        # Allow any model routed via OpenRouter (e.g. fetched dynamically from OR API)
        config = config_manager.load_config()
        if config_manager.is_provider_ready("openrouter", config):
            self.active_model = model_id
            self.active_provider = "openrouter"
            return True

        return False

    def check_provider_health(self, provider_id: str) -> bool:
        """Proactively checks if a provider's endpoint is reachable."""
        config = config_manager.load_config()
        providers = config.get("providers", {})
        if provider_id not in providers:
            return False
            
        p_cfg = providers[provider_id]
        if not p_cfg.get("enabled", False):
            return False
            
        url = p_cfg.get("endpoint")
        if not url:
            return False
            
        # Improved health check (HEAD request or GET version)
        try:
            if provider_id == "ollama":
                # Ollama specific check - /api/tags is the most reliable "ready" indicator
                base_url = url.replace("/api/chat", "")
                tags_url = f"{base_url.rstrip('/')}/api/tags"
                response = requests.get(tags_url, timeout=2)
                return response.status_code == 200
            else:
                # Generic cloud provider ping is usually not needed/possible without key
                # but for local ones we check reachability
                if provider_id in ["lm_studio", "vllm"]:
                    base_url = url.rsplit('/', 2)[0] # Strip v1/chat/completions
                    response = requests.get(base_url, timeout=2)
                    return response.status_code == 200
            return True # Assume cloud is up if key is present
        except Exception:
            return False

    def get_models(self) -> Dict[str, List[Dict[str, str]]]:
        """Returns enabled models categorized for the UI."""
        self._load_config() # Always fresh
        return self.MODELS

    def _dispatch_call(self, system_prompt: str, user_prompt: str, images: Optional[List[str]] = None) -> str:
        """Raw dispatcher with vision support."""
        provider_cfg = self.providers.get(self.active_provider) or {}
        
        # ...
        if self.active_provider == "openrouter":
            return self._call_openrouter(provider_cfg, system_prompt, user_prompt, images)
        elif self.active_provider == "ollama":
            # ...
            return self._call_ollama(provider_cfg, system_prompt, user_prompt, images)
        elif self.active_provider == "anthropic":
            return self._call_anthropic(provider_cfg, system_prompt, user_prompt, images)
        elif self.active_provider in ["openai", "google", "xai", "mistral", "qwen", "glm", "moonshot", "minimax", "venice", "copilot", "lm_studio", "vllm"]:
            return self._call_openai_compatible(provider_cfg, system_prompt, user_prompt, images)
            
        return f"[Error LLM] Provedor '{self.active_provider}' não suportado ou implementação pendente."

    def generate(self, system_prompt: str, user_prompt: str, task_hint: Optional[str] = None, images: Optional[List[str]] = None) -> str:
        """Routes the generation request to the active provider with vision support."""
        governor.record_llm_call()
        if not governor.can_call_llm():
            return "[Error LLM] Limite de segurança de custos atingido. Bloqueio preventivo ativado."

        # Capture current state for safe restoration
        _original_model = self.active_model
        _original_provider = self.active_provider

        # Governor may request cheapest tier temporarily
        _forced_auto = False
        if governor.fallback_active and not self.auto_strategy:
            logger.warning("Cost Governor engaged: Forcing Auto-Strategy due to high-load limits.")
            _forced_auto = True

        # --- SEMANTIC CACHE LOOKUP ---
        # Don't cache if images are present (for now) or if explicitly disabled
        if not images and task_hint != "UPGRADED":
            cached_res = semantic_cache.lookup(system_prompt, user_prompt)
            if cached_res:
                logger.info("🧠 Arkanis Semantic Cache: HIT", symbol="💎")
                return cached_res

        # --- AUTO-STRATEGY / FAILOVER MODE ---
        if self.auto_strategy or _forced_auto:
            _original_model = self.active_model
            _original_provider = self.active_provider

            category = strategy_engine.classify_task(user_prompt, len(system_prompt))
            fallback_chain = strategy_engine.get_fallback_chain(category)
            
            # Use grouped tiers based on LATEST provider stats
            grouped_tiers = strategy_engine._group_enabled_models(self.all_models)

            print(f"[Strategy] Category: {category}")
            for tier in fallback_chain:
                models_in_tier = grouped_tiers.get(tier, [])
                if not models_in_tier:
                    continue

                for best_model_id in models_in_tier:
                    print(f"[Strategy] Testing priority: {tier} -> {best_model_id}")
                    self.set_model(best_model_id)
                    self.active_tier = tier

                    result = self._dispatch_call(system_prompt, user_prompt)

                    if result and not str(result).startswith("[Error LLM]"):
                        # Success! Cache, restore and return.
                        semantic_cache.store(system_prompt, user_prompt, result)
                        self.active_model = _original_model
                        self.active_provider = _original_provider
                        return result
                    
                    print(f"[Strategy Fallback] {best_model_id} failed. Trying next...")

            # Restore original model on total failure
            self.active_model = _original_model
            self.active_provider = _original_provider
            return "[Error LLM] O sistema falhou em encontrar um modelo disponível em todos os níveis de fallback."

        # --- SMART UPGRADE (Manual or Auto-Low Mode) ---
        # If task is engineering/complex but we are NOT in a high performance tier, force an upgrade
        high_tiers = ["HIGH PERFORMANCE", "BALANCED", "SMART_HIGH PERFORMANCE", "SMART_BALANCED"]
        if task_hint in ["engineering", "complex"] and self.active_tier not in high_tiers:
            logger.info(f"🚀 Smart Upgrade engaged: {task_hint.capitalize()} task detected. Switching to Elite Coding models.", symbol="⚡")
            
            # Save current tier for restoration
            _original_tier = self.active_tier
            
            # Re-run strategy specifically for complex engineering
            config = config_manager.load_config()
            best_model, tier, category = strategy_engine.decide(user_prompt, system_prompt, config.get("models", []))
            
            if tier in high_tiers:
                logger.info(f"🎯 Redirigindo para modelo de Elite: {best_model} ({tier})")
            # 1. Select the BEST available model for the task (prioritizing DeepSeek due to Sonnet 400 issues)
            # Tier mapping: 
            # HIGH PERFORMANCE -> DeepSeek V3
            # BALANCED -> Sonnet 3.5 (Fallback)
            elite_model = "deepseek/deepseek-chat"
            elite_provider = "openrouter"
            
            # Verify if elite_model exists in config, otherwise discovery
            # (In this context, we hardcode for speed of healing)
            
            logger.info(f"🧠 🎯 Redirigindo para modelo de Elite: {elite_model} ({self.active_tier})", symbol="🧠")
            
            # Temporary state switch
            self.active_model = elite_model
            self.active_provider = elite_provider
            
            try:
                res = self.generate(system_prompt, user_prompt, task_hint="UPGRADED")
                
                # Restore original state
                self.active_model = _original_model
                self.active_provider = _original_provider
                self.active_tier = _original_tier
                
                if res and not str(res).startswith("[Error LLM]"):
                    # Generate will store it if successful
                    return res
                logger.warning("⚠️ Elite call failed. Falling back to original model...")
            except Exception as e:
                logger.error(f"Error during smart upgrade: {str(e)}")
                # Restore state even on crash
                self.active_model = _original_model
                self.active_provider = _original_provider
                self.active_tier = _original_tier

        # --- MANUAL MODE ---
        self.active_tier = "MANUAL"
        
        start_time = time.time()
        logger.request(self.active_provider, self.active_model)
        
        result = self._dispatch_call(system_prompt, user_prompt)
        duration = time.time() - start_time
        
        # Automatic failover even in manual mode if primary fails
        if result and str(result).startswith("[Error LLM]"):
            logger.warning(f"Active model {self.active_model} failed. Attempting silent recovery...")
            # 1. Trigger fresh discovery
            self._discover()
            # 2. Retry call with new discovery
            logger.info(f"Retrying with re-discovered model: {self.active_model} ({self.active_provider})", symbol="🔄")
            retry_result = self._dispatch_call(system_prompt, user_prompt)
            if retry_result and not str(retry_result).startswith("[Error LLM]"):
                semantic_cache.store(system_prompt, user_prompt, retry_result)
                logger.response(success=True, duration=time.time() - start_time)
                return retry_result
                
            # 3. Last chance: Absolute Auto-Strategy
            logger.info("Universal failover activated (Auto-Strategy).", symbol="🛡️")
            self.auto_strategy = True
            final_retry = self.generate(system_prompt, user_prompt)
            self.auto_strategy = False # Revert state
            return final_retry

        if result and not str(result).startswith("[Error LLM]"):
            semantic_cache.store(system_prompt, user_prompt, result)
            logger.response(success=True, duration=duration)
        else:
            logger.response(success=False)
            
        return result


    def _call_openrouter(self, cfg: Dict, system_prompt: str, user_prompt: str, images: Optional[List[str]] = None) -> str:
        api_key = cfg.get("api_key", "").strip()
        if not api_key:
            return "[Error LLM] API Key do OpenRouter não configurada."

        url = cfg.get("endpoint", "https://openrouter.ai/api/v1/chat/completions").strip()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "Arkanis V3 Agent OS",
            "HTTP-Referer": "https://github.com/arkanis-ai/v3"
        }
        
        # Multi-modal payload
        user_content = user_prompt
        if images:
            user_content = [{"type": "text", "text": user_prompt}]
            for img in images:
                if not img.startswith("data:"):
                    img = f"data:image/jpeg;base64,{img}"
                user_content.append({"type": "image_url", "image_url": {"url": img}})

        payload = {
            "model": self.active_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            
            if not response.ok:
                error_body = response.text
                try:
                    err_json = response.json()
                    error_msg = err_json.get("error", {}).get("message", error_body)
                except:
                    error_msg = error_body
                return f"[Error LLM] Erro na chamada OpenRouter ({response.status_code}): {error_msg}"

            response.raise_for_status()
            data = response.json()
            choices = data.get('choices', [])
            if not choices:
                return f"[Error LLM] OpenRouter retornou lista vazia: {data}"
            
            content = choices[0].get('message', {}).get('content', '')
            if content is None:
                return "[Error LLM] OpenRouter retornou conteúdo nulo."
            return content.strip()
        except requests.exceptions.Timeout:
            return "[Error LLM] OpenRouter timeout (Conexão lenta ou instável)."
        except Exception as e:
            return f"[Error LLM] Erro na chamada OpenRouter: {str(e)}"

    def _call_ollama(self, cfg: Dict, system_prompt: str, user_prompt: str, images: Optional[List[str]] = None) -> str:
        url = cfg.get("endpoint", "http://localhost:11434/api/chat")
        
        # Ollama expects images as a list of base64 strings (without data prefix)
        ollama_images = []
        if images:
            for img in images:
                if img.startswith("data:"):
                    ollama_images.append(img.split(",")[1])
                else:
                    ollama_images.append(img)

        payload = {
            "model": self.active_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt, "images": ollama_images if ollama_images else None}
            ],
            "stream": False
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data['message']['content'].strip()
        except Exception as e:
            return f"[Error LLM] Ollama em {url} falhou: {str(e)}"

    def _call_anthropic(self, cfg: Dict, system_prompt: str, user_prompt: str, images: Optional[List[str]] = None) -> str:
        api_key = cfg.get("api_key")
        if not api_key:
            return "[Error LLM] API Key da Anthropic não configurada."

        url = cfg.get("endpoint", "https://api.anthropic.com/v1/messages")
        
        # Anthropic multi-modal format
        user_content = [{"type": "text", "text": user_prompt}]
        if images:
            for img in images:
                b64_data = img.split(",")[1] if img.startswith("data:") else img
                user_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64_data
                    }
                })

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2024-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.active_model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_content}
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            content_list = data.get('content', [])
            if not content_list:
                return f"[Error LLM] Anthropic retornou lista vazia: {data}"
            return content_list[0].get('text', '').strip()
        except Exception as e:
            return f"[Error LLM] Anthropic falhou: {str(e)}"

    def _call_openai_compatible(self, cfg: Dict, system_prompt: str, user_prompt: str, images: Optional[List[str]] = None) -> str:
        url = cfg.get("endpoint")
        if not url:
            return f"[Error LLM] Endpoint para {self.active_provider} não configurado."

        headers = {"Content-Type": "application/json"}
        api_key = cfg.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # OpenAI multi-modal format
        user_content = user_prompt
        if images:
            user_content = [{"type": "text", "text": user_prompt}]
            for img in images:
                if not img.startswith("data:"):
                    img = f"data:image/jpeg;base64,{img}"
                user_content.append({"type": "image_url", "image_url": {"url": img}})

        payload = {
            "model": self.active_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "max_tokens": 4096
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            choices = data.get('choices', [])
            if not choices:
                return f"[Error LLM] {self.active_provider.upper()} retornou lista vazia: {data}"
            content = choices[0].get('message', {}).get('content', '')
            if content is None:
                return f"[Error LLM] {self.active_provider.upper()} retornou conteúdo nulo."
            return content.strip()
        except Exception as e:
            return f"[Error LLM] {self.active_provider.upper()} falhou: {str(e)}"

# Singleton Instance
router = LLMRouter()
