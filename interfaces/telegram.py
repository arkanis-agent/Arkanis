import os
import time
import requests
import json
import re
from uuid import uuid4
from rich.console import Console
from rich.panel import Panel

# Constants for maintainability
MAX_MESSAGE_LENGTH = 4000
AUDIO_SAVE_DIR = "data"
TELEGRAM_CHAT_ACTION_TIMEOUT = 5
REQUEST_TIMEOUT = 35
AUDIO_DOWNLOAD_TIMEOUT = 30

# Pattern to strip potentially dangerous characters from error messages
def sanitize_error_message(text: str) -> str:
    """Remove Python exception details that could expose internal system info."""
    return re.sub(r"\bException\b|\bError\b|\bTraceback\b|\bFile \"[^"]*\"\b|\bLine \d+\b", "", str(text), flags=re.IGNORECASE)

class TelegramInterface:
    """
    Telegram Bot Interface for ARKANIS V3.
    Polls the Telegram API via simple requests and forwards commands to the Agent Kernel.
    """
    def __init__(self, agent):
        self.agent = agent
        self.console = Console()
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not self.token:
            self.console.print("[red]Critical Error: TELEGRAM_BOT_TOKEN environment variable not set.[/red]")
            self.console.print("[yellow]Hint: Ensure your .env file or environment has the token configured.[/yellow]")
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0

    def _safe_cleanup_path(self, file_path: str) -> None:
        """Safely delete a file, ignoring missing file errors."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass  # Silent cleanup failures to avoid secondary errors

    def start_loop(self):
        """Starts the long-polling loop to get messages from Telegram."""
        if not self.token:
            return

        self.console.print(Panel(
            "Telegram Interface Online.\nPolling for messages... (Press Ctrl+C to stop)",
            title="[bold blue]ARKANIS TELEGRAM BOT[/bold blue]",
            style="cyan"
        ))

        while True:
            try:
                updates = self._get_updates()
                for update in updates:
                    self.last_update_id = update["update_id"]
                    self._process_update(update)
            except KeyboardInterrupt:
                self.console.print("\n[red]Exiting Telegram Interface...[/red]")
                break
            except Exception as e:
                self.console.print(f"[red]Event Loop Error: {sanitize_error_message(e)}[/red]")
                time.sleep(5)
            
            time.sleep(1)

    def _get_updates(self):
        """Fetches updates from the Telegram API via long-polling offset."""
        if not self.token:
            return []
            
        url = f"{self.api_url}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 30}
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return data.get("result", [])
            else:
                error_desc = data.get('description', 'Unknown Error')
                self.console.print(f"[red]Telegram API Error: {error_desc}[/red]")
                self.agent.log(f"Telegram API Error: {error_desc}", "error")
                return []
        except requests.exceptions.RequestException as e:
            if "ReadTimeout" not in str(e) and "timeout" not in str(e).lower():
                self.console.print(f"[yellow]Polling warning: {sanitize_error_message(e)}[/yellow]")
                self.agent.log(f"Telegram Polling connection issue: {sanitize_error_message(e)}", "warning")
            return []

    def _process_update(self, update):
        """Extracts message and routes to the Agent."""
        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        user_name = message["from"].get("first_name", "User")
        user_text = message.get("text")
        
        # Only write to .env if admin ID is missing and variable exists as key
        if not os.environ.get("TELEGRAM_ADMIN_ID"):
            try:
                with open(".env", "a") as f:
                    f.write(f"\nTELEGRAM_ADMIN_ID={chat_id}\n")
                os.environ["TELEGRAM_ADMIN_ID"] = str(chat_id)
                self.console.print(f"[bold cyan]TELEGRAM_ADMIN_ID vinculado automaticamente ao usu\u00e1rio {user_name} ({chat_id})[/bold cyan]")
            except Exception as e:
                self.console.print(f"[yellow]Could not update .env with TELEGRAM_ADMIN_ID: {sanitize_error_message(e)}[/yellow]")

        # Handle Voice/Audio messages
        if "voice" in message or "audio" in message:
            audio_info = message.get("voice") or message.get("audio")
            file_id = audio_info["file_id"]
            self.console.print(f"[cyan]Telegram ({user_name}):[/cyan] [italic]Enviou uma mensagem de voz/\u00e1udio.[/italic]")
            
            user_text = self._handle_telegram_audio(chat_id, file_id)
            if not user_text:
                return
        
        if not user_text:
            return

        self.console.print(f"[green]Telegram ({user_name}):[/green] {sanitize_error_message(user_text)}")

        # Send a typing indicator for UX
        self._send_chat_action(chat_id, "typing")

        try:
            response = self.agent.handle_input(user_text)
            self._send_message(chat_id, response)
        except Exception as e:
            error_msg = sanitize_error_message(e)
            self.console.print(f"[red]{error_msg}[/red]")
            self._send_message(chat_id, error_msg)

    def _send_message(self, chat_id, text):
        """Sends a text message back to the user, chunking if necessary."""
        url = f"{self.api_url}/sendMessage"
        # Telegram max message length is 4096 characters
        max_length = MAX_MESSAGE_LENGTH
        for i in range(0, len(text), max_length):
            chunk = text[i:i + max_length]
            payload = {"chat_id": chat_id, "text": chunk}
            try:
                response = requests.post(url, json=payload)
                response.raise_for_status()
            except Exception:
                self.console.print(f"[red]Failed to send message to user[/red]")

    def _send_chat_action(self, chat_id, action="typing"):
        """Sends a UI state (like 'typing...') to the chat."""
        url = f"{self.api_url}/sendChatAction"
        payload = {"chat_id": chat_id, "action": action}
        try:
            requests.post(url, json=payload, timeout=TELEGRAM_CHAT_ACTION_TIMEOUT)
        except Exception:
            pass

    def _handle_telegram_audio(self, chat_id, file_id) -> str | None:
        """Downloads audio from Telegram, transcribes it, and returns the text."""
        self._send_chat_action(chat_id, "record_audio")
        temp_file_path = None
        try:
            # 1. Get file path from Telegram
            get_file_url = f"{self.api_url}/getFile"
            resp = requests.get(get_file_url, params={"file_id": file_id}, timeout=15)
            file_data = resp.json()
            if not file_data.get("ok"):
                self._send_message(chat_id, "\u274c Erro ao obter link do arquivo de voz.")
                return None
            
            file_path = file_data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            
            # 2. Download to local tmp
            os.makedirs(AUDIO_SAVE_DIR, exist_ok=True)
            temp_file_path = os.path.join(AUDIO_SAVE_DIR, f"tg_voice_{uuid4().hex[:8]}.ogg")
            
            audio_resp = requests.get(download_url, timeout=AUDIO_DOWNLOAD_TIMEOUT)
            with open(temp_file_path, "wb") as f:
                f.write(audio_resp.content)
            
            # 3. Transcribe via STT Tool
            from tools.registry import registry
            stt_tool = registry.get_tool("speech_to_text")
            if not stt_tool:
                self._send_message(chat_id, "\u26a0\ufe0f STT Tool n\u00e3o registrada no kernel.")
                return None
            
            self._send_chat_action(chat_id, "typing")
            result_json = stt_tool.execute(audio_path=temp_file_path)
            res = json.loads(result_json)
            
            if "error" in res:
                self._send_message(chat_id, f"\u274c Erro na transcri\u00e7\u00e3o: {sanitize_error_message(res['error'])}")
                return None
            
            transcription = res.get("text", "")
            if not transcription:
                self._send_message(chat_id, "\ud83e\udd14 N\u00e3o consegui entender o \u00e1udio.")
                return None
            
            self._send_message(chat_id, f"\ud83c\udf99\ufe0f _Transcri\u00e7\u00e3o:_ \"{sanitize_error_message(transcription)}\"")
            return transcription
            
        except Exception as e:
            self.console.print(f"[red]Telegram Audio Error: {sanitize_error_message(e)}[/red]")
            self._send_message(chat_id, f"\u274c Erro cr\u00edtico ao processar \u00e1udio: {sanitize_error_message(e)}")
            return None
        finally:
            # Cleanup temp file in all cases
            if temp_file_path:
                self._safe_cleanup_path(temp_file_path)