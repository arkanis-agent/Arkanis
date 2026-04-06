import os
import json
import time
import datetime
import tempfile
import threading
from threading import Thread
from typing import Dict, Any, Optional

class SchedulerAgent:
    """
    ARKANIS V3.1 - Scheduler Background Agent
    Continuously monitors the pending reminders database and dispatches notifications
    when a scheduled time is reached.
    """
    def __init__(self, kernel, check_interval: int = 60):
        self.kernel = kernel
        self.reminders_file = os.path.join("data", "reminders.json")
        self.running = False
        self._lock = threading.Lock()
        self._check_interval = check_interval
        
    def start_loop(self):
        """Starts the background checking thread."""
        with self._lock:
            if self.running:
                return
            self.running = True
        
        thread = Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        self.kernel.log("Scheduler Agent initialized and tracking temporal events.", "system")
        
    def stop_loop(self):
        """Stops the background loop gracefully."""
        with self._lock:
            self.running = False

    def _monitor_loop(self):
        while self.running:
            try:
                self._check_reminders()
            except Exception as e:
                self.kernel.log(f"Scheduler Agent error: {e}", "error")
                
            # Sleep with interruption support
            for _ in range(self._check_interval):
                if not self.running:
                    break
                time.sleep(1)
                
    def _check_reminders(self):
        if not os.path.exists(self.reminders_file):
            return
            
        reminders = None
        with self._lock:
            with open(self.reminders_file, "r", encoding="utf-8") as f:
                try:
                    reminders = json.load(f)
                except json.JSONDecodeError:
                    reminders = {}
                
                now = datetime.datetime.now()
                has_changes = False
                pending_updates = []
                
                for r_id, r_data in reminders.items():
                    if r_data.get("status") != "pending":
                        continue
                    
                    trigger_time_str = r_data.get("trigger_time")
                    if not trigger_time_str:
                        continue
                        
                    try:
                        trigger_time = datetime.datetime.strptime(trigger_time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                        
                    if now >= trigger_time:
                        pending_updates.append(r_id)
                        has_changes = True
                        
                # Apply updates with proper locking
                r_id_queue = []
                for r_id in pending_updates:
                    r_data = reminders.get(r_id)
                    if r_data:
                        r_data["status"] = "completed"
                        r_data["completed_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
                        self._dispatch_notification(r_data)
                
        # Atomic write outside lock
        if has_changes and reminders is not None:
            self._atomic_write(json.dumps(reminders, indent=4, ensure_ascii=False))

    def _atomic_write(self, content: str):
        """Write JSON data atomically using temp file + rename."""
        dir_path = os.path.dirname(self.reminders_file)
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=dir_path,
            delete=False
        ) as temp_f:
            temp_path = temp_f.name
            temp_f.write(content)
        
        os.replace(temp_path, self.reminders_file)

    def _dispatch_notification(self, reminder_data: Dict[str, Any]):
        desc = reminder_data.get("description", "Notificação do Sistema")
        created = reminder_data.get("created_at", "Desconhecido")
        
        log_msg = f"[LEMBRETE ALCANÇADO] {desc}"
        self.kernel.log(log_msg, "system")
        
        # Dispatch via Telegram if configured
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        telegram_admin = os.environ.get("TELEGRAM_ADMIN_ID")
        
        if telegram_token and telegram_admin:
            try:
                import requests
                msg = f"🔔 *Arkanis Lembrete Ativo*\n\n_Agendado para agora:_\n{desc}\n\n(Create in: {created})"
                url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                requests.post(url, json={
                    "chat_id": telegram_admin,
                    "text": str(msg),
                    "parse_mode": "MarkdownV2"
                }, timeout=10)
            except Exception as e:
                self.kernel.log(f"Falha ao enviar lembrete via Telegram: {e}", "warning")
