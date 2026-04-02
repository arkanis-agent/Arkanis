import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

# Arkanis Production Logger Engine
# Senior Observability & Systems Engineer Approved

class ArkanisLogger:
    """
    Dual-Layer Logging System
    - Layer 1 (Human): Beautiful, emoji-rich console output.
    - Layer 2 (System): Structured JSON for debugging & analytics.
    """
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_file = os.path.join(self.base_dir, "arkanis.json.log")
        self.human_log_file = os.path.join(self.base_dir, "arkanis.log")

    def _write_system_log(self, level: str, message: str, data: Optional[Dict] = None):
        """Append structured JSON to the system log file."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data or {}
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
            # Also write to human-readable log for tailing
            with open(self.human_log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [{level.upper()}] {message}\n")
        except Exception:
            pass

    def info(self, msg: str, symbol: str = "🧠"):
        """User-friendly information log."""
        print(f"{symbol} {msg}")
        self._write_system_log("info", msg)

    def success(self, msg: str):
        """User-friendly success log."""
        print(f"🟢 {msg}")
        self._write_system_log("success", msg)

    def warning(self, msg: str):
        """User-friendly warning log."""
        print(f"⚠️  {msg}")
        self._write_system_log("warning", msg)

    def error(self, msg: str, fix: Optional[str] = None):
        """User-friendly error log with optional fix suggestion."""
        print(f"🔴 {msg}")
        if fix:
            print(f"   👉 Fix: {fix}")
        self._write_system_log("error", msg, {"fix_suggestion": fix} if fix else None)

    def request(self, provider: str, model: str):
        """Specific lifecycle log for LLM request start."""
        msg = f"Using {provider.title()} AI ({model})"
        print(f"🧠 {msg}")
        print("📨 Sending request...")
        self._write_system_log("request_start", msg, {"provider": provider, "model": model})

    def response(self, success: bool = True, duration: Optional[float] = None):
        """Specific lifecycle log for LLM response end."""
        if success:
            dur_str = f" ({duration:.1f}s)" if duration else ""
            print(f"📩 Response received successfully{dur_str}")
            self._write_system_log("request_end", "Success", {"duration": duration})
        else:
            print("❌ Response failed")
            self._write_system_log("request_end", "Failed")

# Singleton instance
logger = ArkanisLogger()
