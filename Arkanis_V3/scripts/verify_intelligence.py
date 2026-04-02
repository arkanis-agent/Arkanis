import os
import sys

# Arkanis First-Run Validation Script
# Senior Systems Engineer Approved

# Add parent directory to path to enable core imports
V3_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(V3_DIR)

def verify():
    try:
        from core.llm_router import router
        
        if not router or not router.active_model:
            print("\n🔴 AI not responding")
            print("   👉 Suggestion: Run 'arkanis doctor' to fix configuration issues.\n")
            sys.exit(1)

        print("🔍 Validating Arkanis Intelligence...")
        
        # Fast smoke test prompt
        test_prompt = "Hello Arkanis. Respond with 'READY' if you hear me."
        response = router.generate("System Validation.", test_prompt)
        
        if response and "[Error LLM]" not in response:
            print("\n🟢 Arkanis is ready")
            print(f"   AI response working correctly ({router.active_model})\n")
            sys.exit(0)
        else:
            print("\n🔴 AI not responding")
            print(f"   Error: {response[:100]}")
            print("   👉 Suggestion: Run 'arkanis doctor' to fix configuration issues.\n")
            sys.exit(1)
            
    except Exception as e:
        print("\n🔴 System core failure")
        print(f"   Error: {str(e)}")
        print("   👉 Suggestion: Run 'arkanis doctor' to fix configuration issues.\n")
        sys.exit(1)

if __name__ == "__main__":
    verify()
