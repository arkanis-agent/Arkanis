import os
import json
from typing import Dict, Any, List

from core.logger import logger

class ConfigManager:
    """Manages system configuration storage and retrieval."""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Load .env into os.environ if it exists
        env_path = os.path.join(self.base_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(key.strip(), val.strip())

        self.config_dir = os.path.join(self.base_dir, "config")
        self.providers_file = os.path.join(self.config_dir, "providers.json")
        self.integrations_file = os.path.join(self.config_dir, "integrations.json")
        
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """Creates a default providers.json if it doesn't exist."""
        if not os.path.exists(self.providers_file):
            default_config = {
                "providers": {
                    "openrouter": {
                        "name": "OpenRouter",
                        "enabled": True,
                        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
                        "endpoint": "https://openrouter.ai/api/v1/chat/completions"
                    },
                    "ollama": {
                        "name": "Ollama",
                        "enabled": True,
                        "endpoint": "http://localhost:11434/api/chat"
                    },
                    "lm_studio": {
                        "name": "LM Studio",
                        "enabled": False,
                        "endpoint": "http://localhost:1234/v1/chat/completions"
                    },
                    "vllm": {
                        "name": "vLLM",
                        "enabled": False,
                        "endpoint": "http://localhost:8000/v1/chat/completions"
                    }
                },
                "models": [
                    {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "openrouter", "enabled": True},
                    {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "provider": "openrouter", "enabled": True},
                    {"id": "google/gemini-pro-1.5", "name": "Gemini Pro 1.5", "provider": "openrouter", "enabled": True},
                    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openrouter", "enabled": True},
                    {"id": "llama3", "name": "Llama 3 (Ollama)", "provider": "ollama", "enabled": True},
                    {"id": "qwen2", "name": "Qwen 2 (Ollama)", "provider": "ollama", "enabled": True},
                    {"id": "mistral", "name": "Mistral (Ollama)", "provider": "ollama", "enabled": True}
                ]
            }
            self.save_config(default_config)

        if not os.path.exists(self.integrations_file):
            default_integrations_config = {
                "telegram": {
                    "enabled": False,
                    "token": ""
                },
                "supabase": {
                    "enabled": False,
                    "url": "",
                    "anon_key": "",
                    "service_role_key": ""
                },
                "tavily": {
                    "enabled": False,
                    "api_key": ""
                }
            }
            self.save_integrations(default_integrations_config)

    def load_config(self) -> Dict[str, Any]:
        """Loads configuration from JSON and merges with environment variables."""
        try:
            if not os.path.exists(self.providers_file):
                self._ensure_config_exists()
                
            with open(self.providers_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Sync critical keys from environment (Prioritizing ENV over JSON)
            providers = config.get("providers", {})
            
            # OpenRouter
            env_or_key = os.getenv("OPENROUTER_API_KEY")
            if env_or_key:
                logger.info("OpenRouter API Key synchronized from Environment.")
                if "openrouter" not in providers:
                    providers["openrouter"] = {"name": "OpenRouter", "endpoint": "https://openrouter.ai/api/v1/chat/completions"}
                providers["openrouter"]["api_key"] = env_or_key
                providers["openrouter"]["enabled"] = True

            # Anthropic
            env_ant_key = os.getenv("ANTHROPIC_API_KEY")
            if env_ant_key:
                if "anthropic" not in providers:
                    providers["anthropic"] = {"name": "Anthropic", "endpoint": "https://api.anthropic.com/v1/messages"}
                providers["anthropic"]["api_key"] = env_ant_key
                providers["anthropic"]["enabled"] = True

            # OpenAI
            env_oa_key = os.getenv("OPENAI_API_KEY")
            if env_oa_key:
                if "openai" not in providers:
                    providers["openai"] = {"name": "OpenAI", "endpoint": "https://api.openai.com/v1/chat/completions"}
                providers["openai"]["api_key"] = env_oa_key
                providers["openai"]["enabled"] = True
            
            return config
        except Exception as e:
            print(f"[ConfigManager Error] Failed to load config: {str(e)}")
            return {}

    def is_provider_ready(self, provider_id: str, config: Dict[str, Any]) -> bool:
        """Checks if a provider is enabled and has necessary configuration."""
        providers = config.get("providers", {})
        if provider_id not in providers:
            return False
            
        p_cfg = providers[provider_id]
        if not p_cfg.get("enabled", False):
            return False
            
        # Local providers only need endpoint (which is usually defaulted)
        if provider_id in ["ollama", "lm_studio", "vllm"]:
            return bool(p_cfg.get("endpoint"))
            
        # Cloud providers need API key
        return bool(p_cfg.get("api_key"))

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Saves configuration to JSON."""
        try:
            with open(self.providers_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigManager Error] Failed to save providers config: {str(e)}")
            return False

    def load_integrations(self) -> Dict[str, Any]:
        """Loads integrations configuration from JSON."""
        try:
            with open(self.integrations_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ConfigManager Error] Failed to load integrations config: {str(e)}")
            return {}

    def save_integrations(self, config: Dict[str, Any]) -> bool:
        """Saves integrations configuration to JSON."""
        try:
            with open(self.integrations_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigManager Error] Failed to save integrations config: {str(e)}")
            return False

# Singleton
config_manager = ConfigManager()
