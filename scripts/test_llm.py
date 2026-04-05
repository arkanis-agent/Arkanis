import os
import sys
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
        masked = f"{or_key[:10]}...{or_key[-5:]}" if len(or_key) > 15 else "****"
        print(f"[OK] OPENROUTER_API_KEY found in .env: {masked}")
    else:
        print("[WARNING] OPENROUTER_API_KEY not found in .env")

    active_model = os.getenv("ARKANIS_MODEL")
    print(f"[INFO] ARKANIS_MODEL env: {active_model}")
    print(f"[INFO] Router active model: {router.active_model} (Provider: {router.active_provider})")
    print("")

def test_providers():
    print("--- 2. Provider Health Check ---")
    failed_providers = []
    try:
        config = config_manager.load_config()
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}")
        print("")
        return False

    providers = config.get("providers", {})
    for pid, pcfg in providers.items():
        if not pcfg.get("enabled", False):
            continue
        try:
            ready = config_manager.is_provider_ready(pid, config)
            health = router.check_provider_health(pid)
            status = "[OK]" if (ready and health) else "[FAIL]"
            print(f"{status} {pid.upper()}: Ready={ready}, Healthy={health}")
            if not health and pid == "ollama":
                print(f"      (Ollama endpoint {pcfg.get('endpoint')} not reachable)")
                print(f"      👉 SUGGESTION: Run 'bash scripts/ensure_ollama.sh' to start the service.")
            if status == "[FAIL]":
                failed_providers.append(pid)
        except Exception as e:
            print(f"[ERROR] Exception checking provider {pid.upper()}: {e}")
            failed_providers.append(pid)
    print("")
    return len(failed_providers) == 0

def test_generation():
    print("--- 3. Generation Test ---")
    system_prompt = "You are a helpful assistant."
    user_prompt = "Hello! Please respond with a single word: SUCCESS."

    print(f"Testing generation with: {router.active_model}...")
    try:
        result = router.generate(system_prompt, user_prompt)
        if result is None or (isinstance(result, str) and "[Error LLM]" in result):
            print(f"[FAIL] Generation failed or returned empty/error: {result}")
            return False
        else:
            print(f"[OK] Response: {result.strip()}")
            return True
    except Exception as e:
        print(f"[ERROR] Exception during generation: {str(e)}")
        return False

if __name__ == "__main__":
    print("ARKANIS V3 - LLM PIPELINE DIAGNOSTIC\n")
    test_config()
    providers_ok = test_providers()
    gen_ok = test_generation()

    print("Diagnostic Complete.")
    if providers_ok and gen_ok:
        print("[SUCCESS] All checks passed.")
        sys.exit(0)
    else:
        print("[FAILURE] One or more checks failed.")
        sys.exit(1)