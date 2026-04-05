import os
import sys
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Arkanis First-Run Validation Script
# Senior Systems Engineer Approved

# Add parent directory to path to enable core imports
V3_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(V3_DIR)

def verify():
    try:
        logger.info("Starting Arkanis intelligence verification")
        
        from core.llm_router import router
        
        if not hasattr(router, 'active_model') or not router.active_model:
            logger.error("AI router configuration invalid")
            print("\n🔴 [Error] AI System Configuration Invalid")
            print("   ├─ Problem: Router or active model not properly initialized")
            print("   └─ Solution: Run 'arkanis doctor' to diagnose configuration issues\n")
            sys.exit(1)

        print("🔍 [Status] Validating Arkanis Intelligence...")
        logger.info("Performing smoke test with router model: %s", router.active_model)
        
        # Fast smoke test prompt
        test_prompt = "Hello Arkanis. Respond with 'READY' if you hear me."
        response = router.generate("System Validation", test_prompt)
        
        if response and "[Error LLM]" not in response:
            logger.info("AI response validation successful")
            print("\n🟢 [Success] Arkanis Operational")
            print(f"   ├─ Model: {router.active_model}")
            print(f"   └─ Status: Response validated successfully\n")
            sys.exit(0)
        else:
            logger.error("AI response validation failed. Response: %s", response[:100] if response else "None")
            print("\n🔴 [Error] AI Response Invalid")
            print(f"   ├─ Problem: {response[:100] if response else 'No response received'}")
            print("   └─ Solution: Run 'arkanis doctor' to fix configuration issues\n")
            sys.exit(1)
            
    except ImportError as e:
        logger.critical("Core module import failed: %s", str(e))
        print("\n🔴 [Critical] Core System Failure")
        print(f"   ├─ Error: {str(e)}")
        print("   └─ Solution: Reinstall core modules or run 'arkanis doctor'\n")
        sys.exit(1)
    except Exception as e:
        logger.critical("Unexpected error during verification: %s", str(e))
        print("\n🔴 [Critical] Unexpected System Failure")
        print(f"   ├─ Error: {str(e)}")
        print("   └─ Solution: Contact Arkanis Support with this error message\n")
        sys.exit(1)

if __name__ == "__main__":
    verify()