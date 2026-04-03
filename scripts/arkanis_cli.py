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

def verify():
    """Performs a quick intelligence smoke test."""
    print("[Action] Verifying intelligence pipeline...")
    script_path = os.path.join(V3_DIR, "scripts", "verify_intelligence.py")
    subprocess.run([sys.executable, script_path])

def start():
    pid = get_pid()
    if pid:
        print(f"[Info] Arkanis already running (PID: {pid})")
        # Still verify if it's responding
        verify()
        return
    
    print("[Action] Starting Arkanis V3.1 in Web Mode...")
    # Run in background redirecting output to log
    with open(LOG_FILE, "a") as log:
        subprocess.Popen([sys.executable, f"{V3_DIR}/main.py", "--web"], 
                         stdout=log, stderr=log, cwd=V3_DIR)
    
    time.sleep(3) # Give it a bit more time to initialize
    new_pid = get_pid()
    if new_pid:
        print(f"[Success] Arkanis online (PID: {new_pid}) at http://localhost:8000")
        # First-run validation
        verify()
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
    """
    Production-grade System Diagnostic
    Senior Product Engineer Approved
    """
    print("\n🧠 Arkanis System Diagnostic\n")
    
    env = load_env()
    results = {
        "env": {"status": "error", "msg": "Not checked", "fix": ""},
        "local": {"status": "error", "msg": "Not checked", "fix": ""},
        "cloud": {"status": "error", "msg": "Not checked", "fix": ""},
        "model": {"status": "error", "msg": "Not checked", "fix": ""},
        "pipeline": {"status": "error", "msg": "Not tested", "fix": ""},
        "mode": "Unknown",
        "status": "Failed",
        "issues": 0
    }

    # 1. Environment Check
    if os.path.exists(ENV_FILE):
        model = env.get("ARKANIS_MODEL")
        if model:
            results["env"] = {"status": "ok", "msg": f"System configuration found (Active: {model})"}
        else:
            results["env"] = {
                "status": "warning", 
                "msg": "Configuration found but no model selected",
                "fix": "Add 'ARKANIS_MODEL=your-model' to your .env file"
            }
            results["issues"] += 1
    else:
        results["env"] = {
            "status": "error", 
            "msg": "Missing .env configuration file",
            "fix": "Run 'arkanis onboard' or create a .env file from the example"
        }
        results["issues"] += 1

    # 2. Local AI (Ollama)
    if router:
        is_healthy = router.check_provider_health("ollama")
        if is_healthy:
            results["local"] = {"status": "ok", "msg": "Local AI (Ollama) is running and reachable"}
        else:
            try:
                subprocess.run(["ollama", "--version"], capture_output=True, check=True)
                results["local"] = {
                    "status": "error", 
                    "msg": "Local AI is currently offline",
                    "fix": "Run 'ollama serve' in your terminal to start the service"
                }
            except Exception:
                results["local"] = {
                    "status": "error", 
                    "msg": "Local AI (Ollama) is not installed",
                    "fix": "Download and install Ollama from https://ollama.com"
                }
            results["issues"] += 1
    else:
        results["local"] = {"status": "error", "msg": "System core not found", "fix": "Reinstall Arkanis"}
        results["issues"] += 1

    # 3. Cloud AI (OpenRouter)
    or_key = env.get("OPENROUTER_API_KEY")
    if or_key:
        try:
            import requests
            res = requests.get("https://openrouter.ai/api/v1/models", timeout=5)
            if res.status_code == 200:
                results["cloud"] = {"status": "ok", "msg": "Cloud AI (OpenRouter) is connected and reachable"}
            else:
                results["cloud"] = {
                    "status": "warning", 
                    "msg": f"Cloud AI service returned a temporary error ({res.status_code})",
                    "fix": "Check your internet connection or API credits"
                }
                results["issues"] += 1
        except Exception:
            results["cloud"] = {
                "status": "error", 
                "msg": "Cloud AI service is unreachable",
                "fix": "Please check your internet connection"
            }
            results["issues"] += 1
    else:
        results["cloud"] = {
            "status": "warning", 
            "msg": "Cloud AI (OpenRouter) key is missing",
            "fix": "Add your API key to OPENROUTER_API_KEY in the .env file"
        }
        results["issues"] += 1

    # 4. Model Configuration & Auto-Discovery
    if router and router.active_model:
        provider = router.active_provider
        is_auto = os.getenv("ARKANIS_MODEL") is None
        auto_label = " (Auto-Discovered)" if is_auto else ""
        results["model"] = {"status": "ok", "msg": f"Model '{router.active_model}' is active{auto_label}"}
        results["mode"] = router.active_provider.title()
    else:
        results["model"] = {
            "status": "error", 
            "msg": "No active model mapping detected",
            "fix": "Verify your ARKANIS_MODEL setting in the .env file"
        }
        results["issues"] += 1

    # 5. LLM Pipeline Test (NEVER SKIP)
    pipeline_successes = []
    if router:
        # Check all available providers instead of skipping
        providers_to_test = []
        if results["local"]["status"] == "ok": providers_to_test.append("ollama")
        if results["cloud"]["status"] == "ok": providers_to_test.append("openrouter")
        
        if not providers_to_test:
            results["pipeline"] = {
                "status": "error", 
                "msg": "Generation test impossible: No reachable providers",
                "fix": "Fix either Local or Cloud AI issues to continue"
            }
            results["issues"] += 1
        else:
            print("🔄 Testing intelligence pipeline...")
            success_count = 0
            for provider in providers_to_test:
                try:
                    # Temporary switch to test specific provider
                    old_provider = router.active_provider
                    router.active_provider = provider
                    # Note: We use a very light prompt for doctor check
                    result = router.generate("System check.", "Reply: OK")
                    if "OK" in result.upper():
                        success_count += 1
                        pipeline_successes.append(provider.title())
                    router.active_provider = old_provider
                except Exception:
                    pass
            
            if success_count == len(providers_to_test):
                results["pipeline"] = {"status": "ok", "msg": "Intelligence pipeline is fully operational"}
            elif success_count > 0:
                results["pipeline"] = {
                    "status": "warning", 
                    "msg": f"Intelligence pipeline is partially operational ({', '.join(pipeline_successes)} working)",
                    "fix": "Check the failing providers above"
                }
                results["issues"] += 1
            else:
                results["pipeline"] = {
                    "status": "error", 
                    "msg": "Generation tests failed across all reachable providers",
                    "fix": "Check your API credits or system logs"
                }
                results["issues"] += 1

    # --- RENDERING ---
    status_map = {"ok": "🟢", "warning": "🟡", "error": "🔴"}
    
    for cat in ["env", "local", "cloud", "model", "pipeline"]:
        res = results[cat]
        print(f"{status_map[res['status']]} {res['msg']}")
        if res.get("fix"):
            print(f"   👉 Fix: {res['fix']}")

    # --- FINAL DASHBOARD ---
    if results["issues"] == 0:
        results["status"] = "Operational"
        reassurance = "✨ Arkanis is healthy and ready for action!"
    elif results["pipeline"]["status"] == "ok" or results["pipeline"]["status"] == "warning":
        results["status"] = "Degraded" if results["issues"] > 0 else "Operational"
        if len(pipeline_successes) > 0:
            results["status"] = "Operational (Partial)"
            reassurance = f"✅ Arkanis will still work using {pipeline_successes[0]}."
        else:
            reassurance = "⚠️  System is running with limitations."
    else:
        results["status"] = "Critical"
        reassurance = "🚫 Arkanis cannot function without a working LLM pipeline."

    print("\n━━━━━━━━━━━━━━━━━━━━━━━")
    print("🧠 Final Status\n")
    print(f"Mode:   {results['mode']}")
    print(f"Status: {results['status']}")
    print(f"Issues: {results['issues']}")
    print(f"\n{reassurance}")
    print("━━━━━━━━━━━━━━━━━━━━━━━\n")


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
    subparsers.add_parser("verify", help="Verify intelligence pipeline")
    subparsers.add_parser("restart", help="Restart Arkanis service")
    subparsers.add_parser("status", help="Show system status")
    subparsers.add_parser("doctor", help="Run system diagnostics")
    subparsers.add_parser("logs", help="Tail system logs")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start()
    elif args.command == "stop":
        stop()
    elif args.command == "verify":
        verify()
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
