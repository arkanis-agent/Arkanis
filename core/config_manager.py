import os
import json
import stat
import tempfile
from typing import Dict, Any, List
import shutil

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from core.logger import logger


class ConfigManager:
    """Manages system configuration storage and retrieval."""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Carregar .env de forma segura usando python-dotenv se disponível, ou manual
        env_path = os.path.join(self.base_dir, ".env")
        if os.path.exists(env_path):
            if load_dotenv:
                try:
                    load_dotenv(env_path.strip(), override=True)
                except Exception as e:
                    logger.warning(f"Failed to load .env: {str(e)}")
            else:
                # Fallback manual para garantir funcionamento sem deps extras
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            os.environ.setdefault(key.strip(), val.strip())

        self.config_dir = os.path.join(self.base_dir, "config")
        self.providers_file = os.path.join(self.config_dir, "providers.json")
        self.integrations_file = os.path.join(self.config_dir, "integrations.json")
        
        # Criar diretório existente e seguro para concorrência
        os.makedirs(self.config_dir, exist_ok=True)
        self._set_secure_permissions()
            
        self._ensure_config_exists()

    def _set_secure_permissions(self):
        """Sets restricted permissions on config files."""
        for file_path in [self.providers_file, self.integrations_file]:
            if os.path.exists(file_path):
                try:
                    os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
                except Exception:
                    pass

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

    def _sync_provider_env_vars(self, providers: Dict[str, Any]) -> Dict[str, Any]:
        """Centralized logic to sync API keys from environment variables to config providers."""
        env_provider_map = {
            "openrouter": {"env": "OPENROUTER_API_KEY", "name": "OpenRouter", "endpoint": "https://openrouter.ai/api/v1/chat/completions"},
            "anthropic": {"env": "ANTHROPIC_API_KEY", "name": "Anthropic", "endpoint": "https://api.anthropic.com/v1/messages"},
            "openai": {"env": "OPENAI_API_KEY", "name": "OpenAI", "endpoint": "https://api.openai.com/v1/chat/completions"},
            "google": {"env": "GOOGLE_API_KEY", "name": "Google Gemini", "endpoint": "https://generativelanguage.googleapis.com/v1beta/"}
        }
        
        for provider_id, env_info in env_provider_map.items():
            env_key = os.getenv(env_info["env"])
            if env_key:
                if provider_id not in providers:
                    providers[provider_id] = {}
                providers[provider_id].update({
                    "name": env_info["name"],
                    "enabled": True,
                    "api_key": env_key
                })
                # Override endpoint if explicitly defined in map, otherwise keep existing
                if "endpoint" in env_info:
                    providers[provider_id]["endpoint"] = env_info["endpoint"]
        return providers

    def load_config(self) -> Dict[str, Any]:
        """Loads configuration from JSON and merges with environment variables."""
        try:
            if not os.path.exists(self.providers_file):
                # Trigger creation if missing
                self._ensure_config_exists()
                
            with open(self.providers_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            if "providers" not in config:
                config["providers"] = {}
            
            # Centralize environment sync
            config["providers"] = self._sync_provider_env_vars(config["providers"])
            
            logger.info("Configuration loaded successfully.")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"[ConfigManager Error] Invalid JSON in providers file: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"[ConfigManager Error] Failed to load config: {str(e)}")
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

    def _atomic_write(self, file_path: str, data: Dict[str, Any]) -> bool:
        """Safely writes data to file using atomic operation to prevent corruption."""
        file_dir = os.path.dirname(file_path)
        try:
            # Write to temp file in same directory
            fd, temp_path = tempfile.mkstemp(dir=file_dir, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Atomic rename
            os.replace(temp_path, file_path)
            # Set permissions after creation
            self._set_secure_permissions_for_file(file_path)
            return True
        except Exception as e:
            logger.error(f"[ConfigManager Error] Atomic write failed: {str(e)}")
            # Cleanup temp file if exists
            try:
                os.remove(temp_path)
            except Exception:
                pass
            return False

    def _set_secure_permissions_for_file(self, file_path: str):
        """Sets secure permissions (0600) for config files."""
        try:
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Saves configuration to JSON."""
        try:
            # Use atomic write for safety
            return self._atomic_write(self.providers_file, config)
        except Exception as e:
            logger.error(f"[ConfigManager Error] Failed to save providers config: {str(e)}")
            return False

    def load_integrations(self) -> Dict[str, Any]:
        """Loads integrations configuration from JSON."""
        try:
            with open(self.integrations_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[ConfigManager Error] Failed to load integrations config: {str(e)}")
            return {}

    def save_integrations(self, config: Dict[str, Any]) -> bool:
        """Saves integrations configuration to JSON."""
        try:
            return self._atomic_write(self.integrations_file, config)
        except Exception as e:
            logger.error(f"[ConfigManager Error] Failed to save integrations config: {str(e)}")
            return False

# Singleton
config_manager = ConfigManager()
