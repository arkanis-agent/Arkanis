import os
import sys
import subprocess
import argparse
import time

# Arkanis Management CLI
# Senior System Architect Specialist

V3_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(V3_DIR, ".env")
LOG_FILE = os.path.join(V3_DIR, "arkanis.log")

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
    print("----------------------------------------------------------")
    print("           ARKANIS V3.1 - SYSTEM DOCTOR")
    print("----------------------------------------------------------")
    
    # 1. Environment Check
    if os.path.exists(ENV_FILE):
        print("[OK] .env file found.")
    else:
        print("[FAIL] .env file missing. Run 'arkanis onboard'.")
        
    # 2. Ollama Check
    ollama_res = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
    if ollama_res.returncode == 0:
        print(f"[OK] Ollama detected: {ollama_res.stdout.strip()}")
    else:
        print("[FAIL] Ollama not found.")
        
    # 3. Model Check
    env = load_env()
    model = env.get("ARKANIS_MODEL")
    if model:
        models_res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if model in models_res.stdout:
            print(f"[OK] Intelligence model '{model}' available.")
        else:
            print(f"[FAIL] Local model '{model}' not found. Run 'ollama pull {model}'.")
            
    # 4. Resource Check
    try:
        from scripts.hardware_detect import get_ram_gb
        ram = get_ram_gb()
        if ram >= 7.0:
            print(f"[OK] Memory sufficient: {round(ram, 2)} GB.")
        else:
            print(f"[WARN] Memory low: {round(ram, 2)} GB. Performance may suffer.")
    except Exception:
        pass

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
