#!/usr/bin/env python3
# Core imports
import argparse
import os
import sys
import threading
import time

# Third-party imports
import webbrowser
import uvicorn

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(, PROJECT_ROOT)

def load_env_safely():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_path):
        return
    
    forbidden_patterns = ["$", "`", "&&", "\\", "|", ";"]
    
    with open(env_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                print(f"[WARNING] Skipping malformed .env line {line_num}: {line}")
                continue
                
            key, val = line.split("=", 1)
            key = key.strip()
            if not key.isidentifier():
                print(f"[WARNING] Skipping invalid key at line {line_num}: {key}")
                continue
                
            val = val.strip()
            # Remove aspas duplas ou simples circundantes corretamente
            if len(val) >= 2 and ((val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'"))):
                val = val[1:-1]
                
            # Checagem de segurança ampliada
            if any(pattern in val for pattern in forbidden_patterns):
                print(f"[WARNING] Skipping potentially unsafe .env line {line_num}")
                continue
                
            os.environ[key] = val

load_env_safely()

def main():
    parser = argparse.ArgumentParser(description="Arkanis V3 - AI Agent Orchestrator")
    parser.add_argument(
        "mode", 
        nargs="?", 
        default="web", 
        choices=["web", "telegram", "cli"],
        help="Interface de execução: web (padrão) para API/Frontend, telegram, ou cli"
    )
    
    try:
        args = parser.parse_args()
        mode = args.mode
        
        # Atraso na importação dos módulos para melhor performance
        from kernel.planner import Planner
        from kernel.executor import Executor
        from kernel.agent import ArkanisAgent

        print("\n[Boot] Initializing System Core...")
        planner = Planner()
        executor = Executor()
        agent = ArkanisAgent(planner=planner, executor=executor)

        if mode == "telegram":
            from interfaces.telegram import TelegramInterface
            print("[Boot] Initializing Telegram Interface...")
            ui = TelegramInterface(agent)
            ui.start_loop()
        elif mode == "cli":
            from interfaces.cli import ArkanisCLI
            print("[Boot] Initializing Standard CLI...")
            ui = ArkanisCLI(agent)
            ui.start_loop()
        else:
            import api.server as api_server
            print("[Boot] Initializing Web Interface (FastAPI)...")
            print("[INFO] Access ARKANIS at: http://127..0.1:8000")

            def open_browser():
                time.sleep(1.5)
                webbrowser.open("http://127.0.0.1:8000")

            if os.environ.get("ARKANIS_AUTO_OPEN_BROWSER", "true").lower() == "true":
                threading.Thread(target=open_browser, daemon=True).start()

            reload_mode = os.environ.get("ARKANIS_DEBUG", "false").lower() == "true"
            uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=reload_mode)

    except KeyboardInterrupt:
        print("\n\n[System] Forced shutdown detected. Closing memory buffers...")
        sys.exit()
    except Exception as e:
        print(f"\n[Fatal Error] Arkanis V3 crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()