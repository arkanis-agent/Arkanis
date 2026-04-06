import os
import sys
import time
import logging
import argparse
from pathlib import Path
from contextlib import contextmanager

# Colored terminal output
ANSI = {
    'OK': '\033[92m',
    'FAIL': '\033[91m',
    'WARN': '\033[93m',
    'INFO': '\033[94m',
    'END': '\033[0m'
}

def color(text, color_code):
    return f"{color_code}{text}{ANSI['END']}"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add project root to sys.path securely
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.llm_router import router
    from core.config_manager import config_manager
except ImportError as e:
    logger.error(f"[CRITICAL] Error importing core modules: {e}")
    sys.exit(1)

result_stats = {'passed': 0, 'failed': 0}

def _mask_key(key: str) -> str:
    """Safely mask sensitive keys for display."""
    if not key:
        return "None"
    if len(key) < 15:
        return "***masked***"
    return f"{key[:5]}...{key[-4:]}"

@contextmanager
def timeout(seconds):
    def handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds}s")
    import signal
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)

def test_config() -> bool:
    logger.info("--- 1. Configuration Check ---")
    passed = 0
    failed = 0
    
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        print(f"{color('[OK]', 'OK')} OPENROUTER_API_KEY found: {_mask_key(or_key)}")
        passed += 1
    else:
        print(f"{color('[WARNING]', 'WARN')} OPENROUTER_API_KEY not found in environment")
        failed += 1
    
    active_model = os.getenv("ARKANIS_MODEL")
    print(f"{color('[INFO]', 'INFO')} ARKANIS_MODEL env: {active_model}")
    print(f"{color('[INFO]', 'INFO')} Router active model: {router.active_model}")
    print(f"{color('[INFO]', 'INFO')} Router provider: {router.active_provider}")
    
    result_stats['passed'] += passed
    result_stats['failed'] += failed
    return failed == 0

def test_providers() -> bool:
    logger.info("--- 2. Provider Health Check ---")
    passed = 0
    failed = 0
    retry_count = 3
    
    try:
        config = config_manager.load_config()
        if not config:
            print(f"{color('[FAIL]', 'FAIL')} Configuration file empty or could not be loaded.")
            failed += 1
            return False
    except Exception as e:
        print(f"{color('[ERROR]', 'FAIL')} Failed to load config: {e}")
        failed += 1
        return False
    
    providers = config.get("providers", {})
    if not providers:
        print(f"{color('[WARNING]', 'WARN')} No providers found in configuration.")
        failed += 1
        return False
    
    for pid, pcfg in providers.items():
        if not pcfg.get("enabled", False):
            continue
        
        try:
            ready = False
            health = False
            
            for attempt in range(retry_count):
                try:
                    ready = config_manager.is_provider_ready(pid, config)
                    health = router.check_provider_health(pid)
                    if ready and health:
                        break
                except Exception as ex:
                    if attempt < retry_count - 1:
                        time.sleep(1)
                    else:
                        raise
            
            status = color("[OK]", "OK") if (ready and health) else color("[FAIL]", "FAIL")
            print(f"{status} {pid.upper()}: Ready={ready}, Healthy={health}")
            
            if not health and pid == "ollama":
                print(f"      (Ollama endpoint {pcfg.get('endpoint')} not reachable)")
                print(f"      SUGGESTION: Run 'bash scripts/ensure_ollama.sh' to start service.")
        except Exception as e:
            print(f"{color('[ERROR]', 'FAIL')} {pid.upper()} check failed: {e}")
            failed += 1
    
    result_stats['passed'] += passed
    result_stats['failed'] += failed
    return failed == 0

def test_generation() -> bool:
    logger.info("--- 3. Generation Test ---")
    generated = False
    
    system_prompt = "You are a helpful assistant."
    user_prompt = "Hello! Please respond with a single word: SUCCESS."
    
    if not router.active_model:
        print(f"{color('[FAIL]', 'FAIL')} No active model configured for generation.")
        result_stats['failed'] += 1
        return False
    
    print(f"Testing generation with: {router.active_model}...")
    try:
        with timeout(60):  # 60 second timeout
            result = router.generate(system_prompt, user_prompt)
            
        if result is None:
            print(f"{color('[FAIL]', 'FAIL')} Generation returned None")
            result_stats['failed'] += 1
            return False
        elif "[Error LLM]" in str(result):
            print(f"{color('[ERROR]', 'FAIL')} LLM Provider Error: {result}")
            result_stats['failed'] += 1
            return False
        else:
            print(f"{color('[OK]', 'OK')} Response: {result.strip()[:100]}{'...' if len(result) > 100 else ''}")
            generated = True
    except TimeoutError:
        print(f"{color('[TIMEOUT]', 'WARN')} Generation timed out after 60s")
        result_stats['failed'] += 1
        return False
    except Exception as e:
        print(f"{color('[ERROR]', 'FAIL')} Exception: {type(e).__name__}: {str(e)}")
        result_stats['failed'] += 1
        return False
    
    result_stats['passed'] += 1
    return generated

def run_tests(args):
    tests = [test_config, test_providers, test_generation]
    if args.filter:
        test_names = {'config': 0, 'providers': 1, 'generate': 2}
        if args.filter in test_names:
            tests = [tests[test_names[args.filter]]]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test_func.__name__} crashed: {e}")
            results.append(False)
            result_stats['failed'] += 1
    
    print("\n" + "=" * 50)
    print(f"{color('DIAGNOSTIC SUMMARY', 'INFO')}")
    print(f"{color('Passed:', 'OK')} {result_stats['passed']}")
    print(f"{color('Failed:', 'FAIL')} {result_stats['failed']}")
    print(f"{color('Total:', 'INFO')} {len(results)}")
    print("=" * 50)
    
    all_passed = all(results)
    if all_passed:
        print(f"{color('ALL TESTS PASSED', 'OK')}\n")
        sys.exit(0)
    else:
        print(f"{color('SOME TESTS FAILED', 'WARN')}\n")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARKANIS V3 - LLM Pipeline Diagnostic")
    parser.add_argument("--filter", choices=['config', 'providers', 'generate'],
                        help="Run only specific test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    print(f"{color('ARKANIS V3 - LLM PIPELINE DIAGNOSTIC\n', 'INFO')}")
    run_tests(args)