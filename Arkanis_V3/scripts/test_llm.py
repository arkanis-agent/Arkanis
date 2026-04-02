import os
import sys
import requests
import json
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from core.llm_router import router
    from core.config_manager import config_manager
except ImportError as e:
    print(f"Error importing core modules: {e}")
    sys.exit(1)

def test_config():
    print("--- 1. Configuration Check ---")
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        print(f"[OK] OPENROUTER_API_KEY found in .env: {or_key[:10]}...{or_key[-5:]}")
    else:
        print("[WARNING] OPENROUTER_API_KEY not found in .env")

    active_model = os.getenv("ARKANIS_MODEL")
    print(f"[INFO] ARKANIS_MODEL env: {active_model}")
    print(f"[INFO] Router active model: {router.active_model} (Provider: {router.active_provider})")
    print("")

def test_providers():
    print("--- 2. Provider Health Check ---")
    config = config_manager.load_config()
    providers = config.get("providers", {})
    
    for pid, pcfg in providers.items():
        if not pcfg.get("enabled", False):
            continue
            
        ready = config_manager.is_provider_ready(pid, config)
        health = router.check_provider_health(pid)
        
        status = "[OK]" if (ready and health) else "[FAIL]"
        print(f"{status} {pid.upper()}: Ready={ready}, Healthy={health}")
        if not health and pid == "ollama":
            print(f"      (Ollama endpoint {pcfg.get('endpoint')} not reachable)")
    print("")

def test_generation():
    print("--- 3. Generation Test ---")
    system_prompt = "You are a helpful assistant."
    user_prompt = "Hello! Please respond with a single word: SUCCESS."
    
    print(f"Testing generation with: {router.active_model}...")
    try:
        result = router.generate(system_prompt, user_prompt)
        if "[Error LLM]" in result:
            print(f"[FAIL] Generation failed: {result}")
        else:
            print(f"[OK] Response: {result}")
    except Exception as e:
        print(f"[ERROR] Exception during generation: {str(e)}")
    print("")

if __name__ == "__main__":
    print("ARKANIS V3 - LLM PIPELINE DIAGNOSTIC\n")
    test_config()
    test_providers()
    test_generation()
    print("Diagnostic Complete.")
