import os
import json
from typing import Dict, Any
from cryptography.fernet import Fernet
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

VAULT_FILE = os.path.join("data", "vault.enc")

def _get_encryption_key() -> bytes:
    """Retrieve or generate the Fernet key from .env."""
    key = os.environ.get("ARKANIS_VAULT_KEY")
    if not key:
        logger.info("ARKANIS_VAULT_KEY not found. Generating a new one.")
        key_bytes = Fernet.generate_key()
        key = key_bytes.decode('utf-8')
        os.environ["ARKANIS_VAULT_KEY"] = key
        
        # Append to .env file
        try:
            with open(".env", "a", encoding="utf-8") as f:
                f.write(f"\nARKANIS_VAULT_KEY={key}\n")
        except Exception as e:
            logger.error(f"Failed to append vault key to .env: {e}")
            
    return key.encode('utf-8')

def _load_vault_data(f: Fernet) -> Dict[str, Any]:
    """Load and decrypt the vault data."""
    if not os.path.exists(VAULT_FILE):
        return {}
    
    try:
        with open(VAULT_FILE, "rb") as file:
            encrypted_data = file.read()
            if not encrypted_data:
                return {}
            decrypted_data = f.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to decrypt vault: {e}")
        return {}

def _save_vault_data(f: Fernet, data: Dict[str, Any]) -> bool:
    """Encrypt and save the vault data."""
    try:
        os.makedirs(os.path.dirname(VAULT_FILE), exist_ok=True)
        json_data = json.dumps(data).encode('utf-8')
        encrypted_data = f.encrypt(json_data)
        with open(VAULT_FILE, "wb") as file:
            file.write(encrypted_data)
        return True
    except Exception as e:
        logger.error(f"Failed to encrypt and save vault: {e}")
        return False


class StoreCredentialTool(BaseTool):
    @property
    def name(self) -> str: return "save_credential"
    
    @property
    def description(self) -> str: 
        return "Saves a credential (url, username, password) securely in the encrypted vault."
        
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "domain": "The website url, domain, or service name.",
            "username": "The login username or email.",
            "password": "The password."
        }
        
    def execute(self, **kwargs) -> str:
        domain = kwargs.get("domain", "").strip()
        username = kwargs.get("username", "").strip()
        password = kwargs.get("password", "")
        
        if not domain or not username or not password:
            return "Error: domain, username, and password are required."
            
        try:
            key = _get_encryption_key()
            f = Fernet(key)
            vault_data = _load_vault_data(f)
            
            # Use domain as key, or allow multiple? Let's use lowercased domain.
            key_name = domain.lower()
            vault_data[key_name] = {
                "url": domain,
                "username": username,
                "password": password
            }
            
            if _save_vault_data(f, vault_data):
                return f"Successfully encrypted and saved credential for {domain}."
            else:
                return "Failed to save credential securely."
        except Exception as e:
            return f"Vault encryption error: {str(e)}"


class RetrieveCredentialTool(BaseTool):
    @property
    def name(self) -> str: return "get_credential"
    
    @property
    def description(self) -> str: 
        return "Retrieves securely stored credentials (username, password) from the encrypted vault by domain/url."
        
    @property
    def arguments(self) -> Dict[str, str]:
        return {"domain": "The website url, domain, or service name to lookup."}
        
    def execute(self, **kwargs) -> str:
        domain = kwargs.get("domain", "").strip()
        if not domain:
            return "Error: domain parameter is required."
            
        try:
            key = _get_encryption_key()
            f = Fernet(key)
            vault_data = _load_vault_data(f)
            
            # Simple matching: see if domain text matches any stored keys
            search_query = domain.lower()
            results = []
            
            for k, cred in vault_data.items():
                if search_query in k:
                    results.append(cred)
                    
            if not results:
                return f"No credentials found matching '{domain}'."
                
            return json.dumps(results, indent=2, ensure_ascii=False)
            
        except Exception as e:
            return f"Vault decryption error: {str(e)}"

# Register tools
try:
    if "save_credential" in registry._tools:
        del registry._tools["save_credential"]
    if "get_credential" in registry._tools:
        del registry._tools["get_credential"]
except Exception:
    pass

registry.register(StoreCredentialTool())
registry.register(RetrieveCredentialTool())
