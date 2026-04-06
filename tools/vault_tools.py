import os
import json
import stat
import fcntl
from typing import Dict, Any
from cryptography.fernet import Fernet
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

VAULT_FILE = os.path.join("data", "vault.enc")
ENV_FILE = ".env"

# Cache global para evitar recriação de Fernet
_FERNET_CACHE = None
_KEY_CACHE = None

def _get_encryption_key() -> bytes:
    """Retrieve or generate the Fernet key from .env with caching."""
    global _KEY_CACHE
    
    if _KEY_CACHE is not None:
        return _KEY_CACHE
    
    key = os.environ.get("ARKANIS_VAULT_KEY")
    if not key:
        logger.warning("ARKANIS_VAULT_KEY not found in environment. Key generation required!")
        key_bytes = Fernet.generate_key()
        key = key_bytes.decode('utf-8')
        _KEY_CACHE = key.encode('utf-8')
        
        # Secure write to .env file with restricted permissions
        try:
            with open(ENV_FILE, "a", encoding="utf-8") as f:
                f.write(f"\nARKANIS_VAULT_KEY={key}\n")
            # Set restrictive file permissions (owner read/write only)
            os.chmod(ENV_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            logger.error(f"Failed to persist vault key: {e}")
            raise
            
    return _KEY_CACHE

def _get_fernet_instance() -> Fernet:
    """Get cached Fernet instance for efficiency."""
    global _FERNET_CACHE
    
    if _FERNET_CACHE is None:
        key = _get_encryption_key()
        _FERNET_CACHE = Fernet(key)
        return _FERNET_CACHE
    
    return _FERNET_CACHE

def _load_vault_data(fernet: Fernet) -> Dict[str, Any]:
    """Load and decrypt the vault data."""
    if not os.path.exists(VAULT_FILE):
        return {}
    
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
        with open(VAULT_FILE, "rb") as file:
            encrypted_data = file.read()
            if not encrypted_data:
                return {}
            decrypted_data = fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
    except json.JSONDecodeError:
        logger.error("Vault data corrupted - cannot decrypt")
        return {}
    except Exception as e:
        logger.error(f"Failed to decrypt vault: {type(e).__name__}")
        return {}

def _save_vault_data(fernet: Fernet, data: Dict[str, Any]) -> bool:
    """Encrypt and save the vault data with proper file permissions."""
    try:
        os.makedirs(os.path.dirname(VAULT_FILE) or ".", exist_ok=True)
        tmp_file = VAULT_FILE + ".tmp"
        
        # Write to temporary file first
        json_data = json.dumps(data).encode('utf-8')
        encrypted_data = fernet.encrypt(json_data)
        
        with open(tmp_file, "wb") as file:
            file.write(encrypted_data)
            file.flush()
            os.fsync(file.fileno())  # Ensure data is written
        
        # Set restrictive file permissions before final move
        os.chmod(tmp_file, stat.S_IRUSR | stat.S_IWUSR)
        
        # Atomic move for integrity
        os.replace(tmp_file, VAULT_FILE)
        return True
    except Exception as e:
        logger.error(f"Failed to save vault: {type(e).__name__}")
        # Clean up temp file if it exists
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        return False


class StoreCredentialTool(BaseTool):
    @property
    def name(self) -> str: return "save_credential"
    
    @property
    def description(self) -> str: 
        return "Securely stores credentials in encrypted vault."
        
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "domain": "Service name or URL (alphanumeric, no special chars recommended).",
            "username": "Login identifier.",
            "password": "Secure password (min 8 chars recommended)."
        }
        
    def execute(self, **kwargs) -> str:
        # Input sanitization and validation
        domain = kwargs.get("domain", "").strip()
        username = kwargs.get("username", "").strip()
        password = kwargs.get("password", "")
        
        # Validation rules
        if not domain or not username or not password:
            return "Error: domain, username, and password are required."
        
        # Sanitize domain - prevent potential injection
        domain = domain.lower().replace(" ", "_-")
        
        # Basic password strength hint
        if len(password) < 8:
            logger.warning("Password may be weak for domain: " + domain)
            return "Warning: password should be at least 8 characters. " + "Credential saved, please update."
        
        try:
            fernet = _get_fernet_instance()
            vault_data = _load_vault_data(fernet)
            
            vault_data[domain] = {
                "url": domain,
                "username": username,
                "password": password,
                "_meta": {"created": "timestamp", "version": 1}
            }
            
            if _save_vault_data(fernet, vault_data):
                return f"Credential for {domain} securely stored."
            return "Failed to save credential."
        
        except Exception as e:
            logger.error("Vault operation failed")
            return "Vault operation failed"


class RetrieveCredentialTool(BaseTool):
    @property
    def name(self) -> str: return "get_credential"
    
    @property
    def description(self) -> str: 
        return "Retrieves stored credentials by domain lookup."
        
    @property
    def arguments(self) -> Dict[str, str]:
        return {"domain": "Service name or URL to search."}
        
    def execute(self, **kwargs) -> str:
        domain = kwargs.get("domain", "").strip()
        if not domain:
            return "Error: domain parameter required."
        
        try:
            fernet = _get_fernet_instance()
            vault_data = _load_vault_data(fernet)
            
            search_query = domain.lower()
            results = []
            
            for key, cred in vault_data.items():
                if search_query in key:
                    results.append(cred)
            
            if not results:
                return "No credentials found."
                
            return json.dumps(results, indent=2, ensure_ascii=False)
        
        except Exception:
            logger.error("Vault retrieval failed")
            return "Credential retrieval failed"


# Safe tool registration
try:
    registry.register(StoreCredentialTool())
    registry.register(RetrieveCredentialTool())
except Exception as e:
    logger.error(f"Vault tool registration failed: {e}")

__all__ = ["StoreCredentialTool", "RetrieveCredentialTool"]

# Module teardown cleanup
import atexit

def _cleanup_vault():
    """Clear sensitive keys from memory on exit."""
    global _FERNET_CACHE, _KEY_CACHE
    _FERNET_CACHE = None
    _KEY_CACHE = None

atexit.register(_cleanup_vault)
