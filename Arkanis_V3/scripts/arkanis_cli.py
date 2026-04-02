import os
import sys
import subprocess
import argparse
import time

# Arkanis Management CLI
# Senior System Architect Specialist

V3_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(V3_DIR) # Enable core imports

ENV_FILE = os.path.join(V3_DIR, ".env")
LOG_FILE = os.path.join(V3_DIR, "arkanis.log")

try:
    from core.llm_router import router
    from core.config_manager import config_manager
except ImportError:
    router = None
    config_manager = None

def load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.strip() and "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    env[key] = val
    return env

def get_pid():
    """Finds the PID of the Arkanis main.py process."""
    try:
        res = subprocess.run(["pgrep", "-f", "main.py --web"], capture_output=True, text=True)
        return res.stdout.strip()
    except Exception:
        return None

def start():
    pid = get_pid()
    if pid:
        print(f"[Info] Arkanis already running (PID: {pid})")
        return
    
    print("[Action] Starting Arkanis V3.1 in Web Mode...")
    # Run in background redirecting output to log
    with open(LOG_FILE, "a") as log:
        subprocess.Popen([sys.executable, f"{V3_DIR}/main.py", "--web"], 
                         stdout=log, stderr=log, cwd=V3_DIR)
    
    time.sleep(2)
    new_pid = get_pid()
    if new_pid:
        print(f"[Success] Arkanis online (PID: {new_pid}) at http://localhost:8000")
    else:
        print("[Error] Failed to start service. Check arkanis.log")

def stop():
    pid = get_pid()
    if not pid:
        print("[Info] Arkanis is not running.")
        return
    
    print(f"[Action] Stopping Arkanis (PID: {pid})...")
    subprocess.run(["kill", pid])
    print("[Success] Background process terminated.")

def restart():
    stop()
    time.sleep(1)
    start()

def status():
    pid = get_pid()
    env = load_env()
    print("----------------------------------------------------------")
    print("           ARKANIS V3.1 - SYSTEM STATUS")
    print("----------------------------------------------------------")
    print(f"Service:   {'[ONLINE]' if pid else '[OFFLINE]'}")
    if pid:
        print(f"PID:       {pid}")
    print(f"Mode:      {env.get('ARKANIS_MODE', 'UNKNOWN')}")
    print(f"Model:     {env.get('ARKANIS_MODEL', 'UNKNOWN')}")
    print(f"WebUI:     http://localhost:8000")
    print("----------------------------------------------------------")

def doctor():
    print("\n🧠 Arkanis System Check\n")
    
    env = load_env()
    all_ok = True

    # 1. Environment Check
    if os.path.exists(ENV_FILE):
        model = env.get("ARKANIS_MODEL")
        if model:
            print(f"🟢 Environment: .env file found (Active: {model})")
        else:
            print("🔴 Environment: .env found but ARKANIS_MODEL missing")
            print("   👉 Fix: Add 'ARKANIS_MODEL=your-model' to your .env file")
            all_ok = False
    else:
        print("🔴 Environment: .env file missing")
        print("   👉 Fix: Run 'arkanis onboard' or create a .env file")
        all_ok = False

    # 2. Local AI (Ollama)
    if router:
        is_healthy = router.check_provider_health("ollama")
        if is_healthy:
            print("🟢 Local AI (Ollama): Service is running and reachable")
        else:
            try:
                subprocess.run(["ollama", "--version"], capture_output=True, check=True)
                print("🔴 Local AI (Ollama): Service not running")
                print("   👉 Fix: Run 'ollama serve' in a new terminal window")
            except Exception:
                print("🔴 Local AI (Ollama): Not installed")
                print("   👉 Fix: Download and install Ollama from https://ollama.com")
            all_ok = False
    else:
        print("🔴 Local AI (Ollama): System core missing (critical error)")
        all_ok = False

    # 3. Cloud AI (OpenRouter)
    or_key = env.get("OPENROUTER_API_KEY")
    if or_key:
        try:
            import requests
            res = requests.get("https://openrouter.ai/api/v1/models", timeout=5)
            if res.status_code == 200:
                print("🟢 Cloud AI: API connected and service reachable")
            else:
                print(f"🟡 Cloud AI: API key present but service error {res.status_code}")
        except Exception:
            print("🔴 Cloud AI: Service unreachable (Check your internet connection)")
            all_ok = False
    else:
        print("🟡 Cloud AI: OpenRouter API key missing")
        print("   👉 Fix: Add your key to OPENROUTER_API_KEY in the .env file")

    # 4. Model Configuration
    if router and router.active_model:
        provider = router.active_provider
        print(f"🟢 Model Config: Active='{router.active_model}' (Provider: {provider})")
    else:
        print("🔴 Model Config: No active model detected")
        print("   👉 Fix: Check your ARKANIS_MODEL setting in .env")
        all_ok = False

    # 5. LLM Pipeline Test
    if all_ok and router:
        print("🔄 LLM Pipeline: Running generation self-test...")
        try:
            result = router.generate("You are a system doctor.", "Respond ONLY with: OK")
            if "OK" in result.upper():
                print("🟢 LLM Pipeline: Real generation successful")
            else:
                print(f"🔴 LLM Pipeline: Test failed (Response: {result[:40]})")
                print("   👉 Fix: Check your API credits or provider status")
                all_ok = False
        except Exception as e:
            print(f"🔴 LLM Pipeline: Error during test ({str(e)})")
            all_ok = False
    else:
        print("🔴 LLM Pipeline: Test skipped due to previous errors")

    if all_ok:
        print("\n✨ Arkanis is healthy and ready for action!\n")
    else:
        print("\n⚠️  System check failed. Please resolve the red 🔴 items above.\n")


def logs():
    if os.path.exists(LOG_FILE):
        subprocess.run(["tail", "-f", LOG_FILE])
    else:
        print("[Error] log file not found.")

def main():
    parser = argparse.ArgumentParser(description="ARKANIS V3.1 Management CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("start", help="Start Arkanis service")
    subparsers.add_parser("stop", help="Stop Arkanis service")
    subparsers.add_parser("restart", help="Restart Arkanis service")
    subparsers.add_parser("status", help="Show system status")
    subparsers.add_parser("doctor", help="Run system diagnostics")
    subparsers.add_parser("logs", help="Tail system logs")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start()
    elif args.command == "stop":
        stop()
    elif args.command == "restart":
        restart()
    elif args.command == "status":
        status()
    elif args.command == "doctor":
        doctor()
    elif args.command == "logs":
        logs()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
