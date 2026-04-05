import os
import json
import time
import datetime
from threading import Thread
from typing import Dict, Any

class SchedulerAgent:
    """
    ARKANIS V3.1 - Scheduler Background Agent
    Continuously monitors the pending reminders database and dispatches notifications
    when a scheduled time is reached.
    """
    def __init__(self, kernel):
        self.kernel = kernel
        self.reminders_file = os.path.join("data", "reminders.json")
        self.running = False
        
    def start_loop(self):
        """Starts the background checking thread."""
        self.running = True
        thread = Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        self.kernel.log("Scheduler Agent initialized and tracking temporal events.", "system")
        
    def stop_loop(self):
        """Stops the background loop."""
        self.running = False

    def _monitor_loop(self):
        while self.running:
            try:
                self._check_reminders()
            except Exception as e:
                self.kernel.log(f"Scheduler Agent error: {e}", "error")
                
            # Sleep for 60 seconds (1 minute interval checking)
            time.sleep(60)
            
    def _check_reminders(self):
        if not os.path.exists(self.reminders_file):
            return
            
        with open(self.reminders_file, "r", encoding="utf-8") as f:
            try:
                reminders = json.load(f)
            except json.JSONDecodeError:
                return # Empty or malformed
                
        now = datetime.datetime.now()
        has_changes = False
        
        for r_id, r_data in list(reminders.items()):
            if r_data.get("status") != "pending":
                continue
                
            trigger_time_str = r_data.get("trigger_time")
            if not trigger_time_str:
                continue
                
            try:
                trigger_time = datetime.datetime.strptime(trigger_time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue # Bad format
                
            if now >= trigger_time:
                # Time to trigger!
                self._dispatch_notification(r_data)
                r_data["status"] = "completed"
                r_data["completed_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
                has_changes = True
                
        if has_changes:
            with open(self.reminders_file, "w", encoding="utf-8") as f:
                json.dump(reminders, f, indent=4, ensure_ascii=False)

    def _dispatch_notification(self, reminder_data: Dict[str, Any]):
        desc = reminder_data.get("description", "Notificação do Sistema")
        created = reminder_data.get("created_at", "Desconhecido")
        
        log_msg = f"[LEMBRETE ALCANÇADO] {desc}"
        self.kernel.log(log_msg, "system")
        
        # Dispatch via Telegram if configured
        import requests
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        telegram_admin = os.environ.get("TELEGRAM_ADMIN_ID")
        
        if telegram_token and telegram_admin:
            msg = f"🔔 *Arkanis Lembrete Ativo*\n\n_Agendado para agora:_\n{desc}\n\n\\(Criado em: {created}\\)"
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            try:
                requests.post(url, json={
                    "chat_id": telegram_admin,
                    "text": msg,
                    "parse_mode": "MarkdownV2"
                }, timeout=10)
            except Exception as e:
                self.kernel.log(f"Falha ao enviar lembrete via Telegram: {e}", "warning")
