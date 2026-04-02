#!/usr/bin/env python3
import sys
import os

# Adjusting python path to allow internal imports relative to /V3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Simple built-in .env loader to avoid external dependencies
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key.strip()] = val.strip()

from kernel.agent import ArkanisAgent
from interfaces.cli import ArkanisCLI
from tools import standard # This triggers tool registration
from tools import system_tools # This triggers system tool registration
from tools import network_tools # This triggers network tool registration
from tools import ai_tools # This triggers AI tool registration
from tools import browser_tools # This triggers browser tool registration
from tools import audio_tools # This triggers audio tool registration

def main():
    """
    Initializes and starts the Arkanis V3 AI Agent OS.
    """
    try:
        # 1. Initialize the Kernel (Agent)
        agent = ArkanisAgent()
        
        # 2. Interface Selection (Default to Web, or CLI/Telegram)
        arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
        
        if arg == "--telegram":
            from interfaces.telegram import TelegramInterface
            print("\n[Boot] Initializing Telegram Interface...")
            ui = TelegramInterface(agent)
            ui.start_loop()
        elif arg == "--cli":
            from interfaces.cli import ArkanisCLI
            print("\n[Boot] Initializing Standard CLI...")
            ui = ArkanisCLI(agent)
            ui.start_loop()
        else:
            # Default to WEB
            import uvicorn
            import webbrowser
            from api.server import app
            
            print("\n[Boot] Initializing Web Interface (FastAPI)...")
            print("[INFO] Access ARKANIS at: http://127.0.0.1:8000")
            
            # Auto-open browser in a separate thread to not block server startup
            def open_browser():
                import time
                time.sleep(1.5)
                webbrowser.open("http://127.0.0.1:8000")
            
            import threading
            threading.Thread(target=open_browser, daemon=True).start()
            
            uvicorn.run(app, host="0.0.0.0", port=8000)
        
    except KeyboardInterrupt:
        print("\n\n[System] Forced shutdown detected. Closing memory buffers...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Fatal Error] Arkanis V3 crashed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
