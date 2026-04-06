import os
import sys
import logging
from typing import Optional

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arkanis_verification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path to enable core imports
V3_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(V3_DIR)

def validate_environment() -> bool:
    """Validate required environment variables and paths."""
    required_dirs = [
        os.path.join(V3_DIR, 'core'),
        os.path.join(V3_DIR, 'scripts')
    ]
    
    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            logger.error("Missing required directory: %s", dir_path)
            return False
    return True

def verify() -> None:
    """Main verification function with improved error handling."""
    try:
        if not validate_environment():
            raise RuntimeError("Environment validation failed")
            
        logger.info("Starting Arkanis intelligence verification")
        
        from core.llm_router import router
        
        if not hasattr(router, 'active_model') or not router.active_model:
            logger.error("AI router configuration invalid. Active model: %s", 
                        getattr(router, 'active_model', 'None'))
            raise ValueError("Router or active model not properly initialized")

        print("🔍 [Status] Validating Arkanis Intelligence...")
        logger.info("Performing smoke test with router model: %s", router.active_model)
        
        test_prompt = "Hello Arkanis. Respond with 'READY' if you hear me."
        if not isinstance(test_prompt, str) or len(test_prompt) > 1000:
            raise ValueError("Invalid test prompt format")
            
        response: Optional[str] = router.generate("System Validation", test_prompt)
        
        if response and "[Error LLM]" not in response:
            logger.info("AI response validation successful. Response: %.30s...", response)
            print(f"\n🟢 [Success] Arkanis Operational")
            print(f"   ├─ Model: {router.active_model}")
            print(f"   └─ Status: Response validated successfully\n")
            sys.exit(0)
        else:
            logger.error("AI response validation failed. Response: %s", 
                        response[:100] if response else "None")
            raise RuntimeError(f"AI Response Invalid: {response[:100] if response else 'No response'}")
            
    except ImportError as e:
        logger.critical("Core module import failed: %s", str(e), exc_info=True)
        raise
    except Exception as e:
        logger.critical("Unexpected error during verification: %s", str(e), exc_info=True)
        raise

if __name__ == "__main__":
    try:
        verify()
    except Exception as e:
        print(f"\n🔴 [Critical] System Failure")
        print(f"   ├─ Error: {str(e)}")
        print(f"   └─ Solution: Check logs at arkanis_verification.log or run 'arkanis doctor'\n")
        sys.exit(1)