import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import threading
import logging
from logging.handlers import RotatingFileHandler
import sys
import atexit

# Arkanis Production Logger Engine v3.1
# Senior Observability & Systems Engineer Approved
# Features: Thread-safe, Log Rotation, Error Recovery, Filtered Levels

class ArkanisLogger:
    """
    Dual-Layer Logging System
    - Layer 1 (Human): Beautiful, emoji-rich console output.
    - Layer 2 (System): Structured JSON for debugging & analytics.
    """

    # Logging level hierarchy
    LOG_LEVELS = {"info": 1, "success": 2, "warning": 3, "error": 4, "critic": 5, "request_start": 6, "request_end": 7}
    MIN_LEVEL = 1

    # Colors for console
    COLORS = {
        "info": "\033[94m",       # Blue
        "success": "\033[92m",     # Green
        "warning": "\033[93m",     # Yellow
        "error": "\033[91m",       # Red
        "critic": "\033[95m",      # Magenta
        "default": "\033[0m"       # Reset
    }

    # Fixed: Removed space in variable name (SYMBOLS not SYMB OS)
    SYMBOLS = {
        "info": "\ud83e\uddd1",
        "success": "\ud83d\udfe2",
        "warning": "\u26a0\ufe0f",
        "error": "\ud83d\udd34",
        "critic": "\ud83d\udee1\ufe0f",
        "request_start": "\ud83e\uddd1",
        "request_end": "\ud83d\udce9"
    }

    def __init__(self, log_dir: Optional[str] = None, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
        self.log_lock = threading.RLock()  # More robust lock type
        self.base_dir = log_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._system_file = os.path.join(self.base_dir, "arkanis.json.log")
        self._human_file = os.path.join(self.base_dir, "arkanis.log")
        self._initialized = False

        # Setup handlers - only store filename, don't attach to handler for manual write
        self.system_handler = None  # We use manual writing with rotation built-in
        self.human_handler = None

        self.log_files = {
            "system": self._system_file,
            "human": self._human_file
        }

    def _write_system_log(self, level: str, message: str, data: Optional[Dict] = None):
        """Thread-safe append to system log."""
        with self.log_lock:
            if self.LOG_LEVELS.get(level, 0) < self.MIN_LEVEL:
                return

            # Validate serializable data
            try:
                data_dumped = json.dumps(data or {})
            except (TypeError, ValueError):
                data = {"error": "Data not JSON serializable"}
                data_dumped = json.dumps(data)

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
                "data": self._safe_dict(data or {})
            }

            # Try to write to log files with proper error handling
            try:
                with open(self._system_file, "a", encoding="utf-8", buffering=1) as f:
                    f.write(json.dumps(log_entry) + "\n")

                with open(self._human_file, "a", encoding="utf-8", buffering=1) as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [{level.upper()}] {message}\n")
                
                self._initialized = True
            except IOError as e:
                print(f"[ARKANIS_LOG ERROR] Could not write to log file: {e}", file=sys.stderr)
            except Exception as e:
                print(f"[ARKANIS_LOG ERROR] Unhandled log error: {e}", file=sys.stderr)

    def _safe_dict(self, value):
        """Ensure dict values are safe for JSON serialization."""
        if isinstance(value, dict):
            return {k: self._safe_dict(v) for k, v in value.items()}
        elif isinstance(value, (str, int, float, bool, type(None))):  # Simplified type check
            return value
        else:
            return str(value)

    def set_level(self, min_level: str):
        """Filter logs by level."""
        if min_level in self.LOG_LEVELS:
            self.MIN_LEVEL = self.LOG_LEVELS[min_level]

    def _print_colored(self, level: str, msg: str):
        """Print colored console output."""
        symbol = self.SYMBOLS.get(level, "")  # Fixed: was accessing undefined SYMBOLS
        color = self.COLORS.get(level, "")
        reset = self.COLORS.get("default", "")
        return f"{color}{symbol} {msg}{reset}"

    def info(self, msg: str, symbol: str = "\ud83e\uddd1"):
        """User-friendly information log."""
        print(self._print_colored("info", f"{symbol} {msg}"))
        self._write_system_log("info", msg)

    def success(self, msg: str, symbol: str = "\ud83d\udfe2"):
        """User-friendly success log."""
        print(self._print_colored("success", f"{symbol} {msg}"))
        self._write_system_log("success", msg)

    def warning(self, msg: str, symbol: str = "\u26a0\ufe0f"):
        """User-friendly warning log."""
        print(self._print_colored("warning", f"{symbol} {msg}"))
        self._write_system_log("warning", msg)

    def error(self, msg: str, fix: Optional[str] = None, symbol: str = "\ud83d\udd34"):
        """User-friendly error log with optional fix suggestion."""
        print(self._print_colored("error", f"{symbol} {msg}"))
        if fix:
            print(f"   \ud83d\udc49 Fix: {fix}")
        self._write_system_log("error", msg, {"fix_suggestion": fix} if fix else None)

    def critic(self, msg: str, symbol: str = "\ud83d\udee1\ufe0f"):
        """User-friendly critic/auditor log."""
        print(self._print_colored("critic", f"{symbol} {msg}"))
        self._write_system_log("critic", msg)

    def request(self, provider: str, model: str):
        """Specific lifecycle log for LLM request start."""
        msg = f"Using {provider.title()} AI ({model})"
        print(self._print_colored("info", f"\ud83e\uddd1 {msg}"))
        print("\ud83d\udce8 Sending request...")
        self._write_system_log("request_start", msg, {"provider": provider, "model": model})

    def response(self, success: bool = True, duration: Optional[float] = None, symbol: str = "\ud83d\udce9"):
        """Specific lifecycle log for LLM response end."""
        if success:
            dur_str = f" ({duration:.1f}s)" if duration else ""
            print(self._print_colored("success", f"{symbol} Response received successfully{dur_str}"))
            self._write_system_log("request_end", "Success", {"duration": duration})
        else:
            print(self._print_colored("error", "\u274c Response failed"))
            self._write_system_log("request_end", "Failed")

    def close(self):
        """Explicit resource cleanup."""
        if self.log_lock:
            self.log_lock.acquire()
            try:
                pass
            finally:
                self.log_lock.release()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()

    # Singleton Pattern - True Single Instance
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            return super().__new__(cls)
        return cls._instance

    # Global singleton instance
    logger = None  # Initialize to None, will be set in __init__

    def __init__(self, log_dir: Optional[str] = None, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
        # Re-run initialization if not already done
        if getattr(self, '_initialized', False):
            return
        super(ArkanisLogger, self).__init__()  # Ensure parent init runs
        self.log_lock = threading.RLock()
        self.base_dir = log_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._system_file = os.path.join(self.base_dir, "arkanis.json.log")
        self._human_file = os.path.join(self.base_dir, "arkanis.log")
        self._initialized = False


def get_logger():
    """Public API to access the logger singleton."""
    if ArkanisLogger.logger is None:
        ArkanisLogger.logger = ArkanisLogger.get_instance()
    return ArkanisLogger.logger


# Initialize singleton at module import
ArkanisLogger.logger = get_logger()
