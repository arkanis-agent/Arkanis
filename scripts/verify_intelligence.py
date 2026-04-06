import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Configure structured logging avoiding duplicate handlers
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler('arkanis_verification.log')
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# Use pathlib for robust path management
CURRENT_FILE = Path(__file__).resolve()
V3_DIR = CURRENT_FILE.parents[1]

if str(V3_DIR) not in sys.path:
    sys.path.append(str(V3_DIR))

def validate_environment() -> bool:
    """Validate required environment variables and paths."""
    required_dirs = [
        V3_DIR / 'core',
        V3_DIR / 'scripts'
    ]
    
    for dir_path in required_dirs:
        if not dir_path.is_dir():
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
        
        active_model = getattr(router, 'active_model', None)
        if not active_model:
            logger.error("AI router configuration invalid. Active model is None or missing")
            raise ValueError("Router or active model not properly initialized")

        print("🔍 [Status] Validating Arkanis Intelligence...")
        logger.info("Performing smoke test with router model: %s", active_model)
        
        test_prompt = "Hello Arkanis. Respond with 'READY' if you hear me."
        # Prompt validation is implicit by being a constant, but kept for logic consistency
        
        response: Optional[str] = router.generate("System Validation", test_prompt)
        
        # Improved validation: check if response exists, is not empty, and doesn't contain error flags
        if response and response.strip() and "[Error LLM]" not in response:
            logger.info("AI response validation successful. Response: %.30s...", response)
            print(f"\n🟢 [Success] Arkanis Operational")
            print(f"   ├─ Model: {active_model}")
            print(f"   └─ Status: Response validated successfully\n")
            sys.exit(0)
        else:
            err_msg = response[:100] if response else "No response received"
            logger.error("AI response validation failed. Response: %s", err_msg)
            raise RuntimeError(f"AI Response Invalid: {err_msg}")
            
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