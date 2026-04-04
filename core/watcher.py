import os
import time
import threading
from typing import Dict, Callable
from core.agent_bus import agent_bus
from core.logger import logger

class ArkanisWatcher:
    """
    Visual Nervous System: Native Polling File Watcher.
    Monitors Arkanis development for changes without external dependencies.
    """
    def __init__(self, target_path: str, excluded_dirs=None):
        self.target_path = target_path
        self.excluded_dirs = excluded_dirs or ['.git', '__pycache__', 'node_modules', '.venv', 'data']
        self.last_snapshot: Dict[str, float] = {}
        self.running = False
        self.thread = None

    def _get_snapshot(self) -> Dict[str, float]:
        """Creates a timestamp snapshot of all monitored files."""
        snapshot = {}
        for root, dirs, files in os.walk(self.target_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            
            for file in files:
                if file.endswith('.py') or file.endswith('.js') or file.endswith('.html') or file.endswith('.css'):
                    full_path = os.path.join(root, file)
                    try:
                        snapshot[full_path] = os.path.getmtime(full_path)
                    except (OSError, FileNotFoundError):
                        pass
        return snapshot

    def _poll_loop(self):
        """Infinite loop for change detection."""
        self.last_snapshot = self._get_snapshot()
        logger.info("[Watcher] Visual Nervous System Active. Monitoring Arkanis Core.")
        
        while self.running:
            time.sleep(2) # Poll every 2 seconds
            current_snapshot = self._get_snapshot()
            
            # Detect changes
            changes = []
            for path, mtime in current_snapshot.items():
                if path not in self.last_snapshot or mtime > self.last_snapshot[path]:
                    changes.append(path)
            
            if changes:
                # Emit system event to AgentBus
                msg = f"Detectada alteração em: {', '.join([os.path.basename(c) for c in changes[:2]])}"
                if len(changes) > 2:
                    msg += f" (e mais {len(changes)-2} arquivos)"
                
                # Broadcast heartbeat to Neural Map
                agent_bus.broadcast_message("system", msg)
                # Mark system as task holder briefly to pulse
                agent_bus.set_task_token("system")
                time.sleep(0.5)
                agent_bus.set_task_token(None)
                
                self.last_snapshot = current_snapshot

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False

# Global instance for the OS
watcher = ArkanisWatcher(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
