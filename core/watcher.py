import os
import time
import threading
from pathlib import Path
from typing import Dict, Callable, List, Optional
from core.agent_bus import agent_bus
from core.logger import logger

class ArkanisWatcher:
    """
    Visual Nervous System: Native Polling File Watcher.
    Monitors Arkanis development for changes without external dependencies.
    """
    
    # Supported file extensions (configurable)
    SUPPORTED_EXTENSIONS = {'.py', '.js', '.html', '.css'}
    
    def __init__(self, target_path: str, excluded_dirs: List[str] = None):
        self.target_path = Path(target_path)
        self.excluded_dirs = excluded_dirs or ['.git', '__pycache__', 'node_modules', '.venv', 'data']
        self.last_snapshot: Dict[str, float] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._poll_interval = 2.0
        logger.info(f"[Watcher] Initialized for {self.target_path}")

    def _get_snapshot(self) -> Dict[str, float]:
        """Creates a timestamp snapshot of all monitored files."""
        snapshot = {}
        try:
            for root, dirs, files in os.walk(self.target_path):
                # Filter excluded directories efficiently
                dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
                
                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext in self.SUPPORTED_EXTENSIONS:
                        full_path = os.path.join(root, file)
                        try:
                            snapshot[full_path] = os.path.getmtime(full_path)
                        except (OSError, FileNotFoundError):
                            continue
        except PermissionError:
            logger.warning(f"[Watcher] Permission denied accessing: {self.target_path}")
        return snapshot

    def _poll_loop(self):
        """Infinite loop for change detection with clean shutdown support."""
        self.last_snapshot = self._get_snapshot()
        logger.info("[Watcher] Visual Nervous System Active. Monitoring Arkanis Core.")
        
        while not self._stop_event.is_set():
            # Use event wait instead of fixed sleep for responsive shutdown
            self._stop_event.wait(timeout=self._poll_interval)
            
            if self._stop_event.is_set():
                break
                
            current_snapshot = self._get_snapshot()
            
            with self._lock:
                changes = []
                for path, mtime in current_snapshot.items():
                    if path not in self.last_snapshot or mtime > self.last_snapshot[path]:
                        changes.append(path)
                
                if changes:
                    self._emit_change_event(changes)
                    self.last_snapshot = self._copy_snapshot(current_snapshot)

    def _emit_change_event(self, changes: List[str]):
        """Emit system event to AgentBus for detected changes."""
        try:
            if agent_bus is None:
                logger.warning("[Watcher] AgentBus not initialized, skipping broadcast")
                return
            
            msg = f"Detectada alteração em: {', '.join([os.path.basename(c) for c in changes[:2]])}"
            if len(changes) > 2:
                msg += f" (e mais {len(changes)-2} arquivos)"
            
            agent_bus.broadcast_message("system", msg)
            self._safe_set_task_token("system")
            time.sleep(min(self._poll_interval / 4, 0.5))
            self._safe_set_task_token(None)
        except Exception as e:
            logger.error(f"[Watcher] Error broadcasting change: {e}")

    def _safe_set_task_token(self, token: Optional[str]):
        """Thread-safe token setter with null check."""
        try:
            agent_bus.set_task_token(token)
        except Exception as e:
            logger.warning(f"[Watcher] Error setting task token: {e}")

    def _copy_snapshot(self, snapshot: Dict[str, float]) -> Dict[str, float]:
        """Thread-safe snapshot copy."""
        return dict(snapshot)

    def start(self) -> bool:
        """Thread-safe start of the watcher."""
        with self._lock:
            if not self.running:
                self.running = True
                self._stop_event.clear()
                self.thread = threading.Thread(target=self._poll_loop, daemon=True, name="ArkanisWatcher")
                self.thread.start()
                logger.info("[Watcher] Started monitoring")
                return True
            logger.debug("[Watcher] Already running")
            return False

    def stop(self, wait: bool = True):
        """Gracefully stop the watcher."""
        with self._lock:
            if self.running:
                self.running = False
                self._stop_event.set()  # Wake up from wait
                self.thread = None  # Clear reference
                
        if wait and hasattr(self, 'thread') and self.thread is not None:
            self.thread.join(timeout=5.0) if self.thread.is_alive() else None
            logger.info("[Watcher] Stopped gracefully")

    def get_snapshot(self) -> Dict[str, float]:
        """Thread-safe snapshot retrieval."""
        with self._lock:
            return dict(self.last_snapshot)

    @property
    def is_active(self) -> bool:
        """Check if watcher is currently running."""
        with self._lock:
            return self.running and self.thread is not None and self.thread.is_alive()

# Global instance for the OS
watcher = ArkanisWatcher(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))