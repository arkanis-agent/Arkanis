import os
import time
import requests
import json
from uuid import uuid4
from rich.console import Console
from rich.panel import Panel

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
                self.console.print(f"[red]Event Loop Error: {e}[/red]")
                time.sleep(5)
            
            time.sleep(1)

    def _get_updates(self):
        """Fetches updates from the Telegram API via long-polling offset."""
        if not self.token:
            return []
            
        url = f"{self.api_url}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 30}
        try:
            response = requests.get(url, params=params, timeout=35) # Slightly longer than polling timeout
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
            # Silent fail for standard ReadTimeouts (expected during long polling)
            if "ReadTimeout" not in str(e) and "timeout" not in str(e).lower():
                self.console.print(f"[yellow]Polling warning: {e}[/yellow]")
                self.agent.log(f"Telegram Polling connection issue: {e}", "warning")
            return []

    def _process_update(self, update):
        """Extracts message and routes to the Agent."""
        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        user_name = message["from"].get("first_name", "User")
        user_text = message.get("text")
        
        # Auto-bind admin ID for proactive notifications if empty
        if not os.environ.get("TELEGRAM_ADMIN_ID"):
            os.environ["TELEGRAM_ADMIN_ID"] = str(chat_id)
            try:
                with open(".env", "a") as f:
                    f.write(f"\nTELEGRAM_ADMIN_ID={chat_id}\n")
                self.console.print(f"[bold cyan]TELEGRAM_ADMIN_ID vinculado automaticamente ao usuário {user_name} ({chat_id})[/bold cyan]")
            except Exception as e:
                pass

        # Handle Voice/Audio messages
        if "voice" in message or "audio" in message:
            audio_info = message.get("voice") or message.get("audio")
            file_id = audio_info["file_id"]
            self.console.print(f"[cyan]Telegram ({user_name}):[/cyan] [italic]Enviou uma mensagem de voz/áudio.[/italic]")
            
            user_text = self._handle_telegram_audio(chat_id, file_id)
            if not user_text:
                return # Error already sent to user
        
        if not user_text:
            return

        self.console.print(f"[green]Telegram ({user_name}):[/green] {user_text}")

        # Send a typing indicator for UX
        self._send_chat_action(chat_id, "typing")

        try:
            # 1. Delegate strictly to the same Kernel handler as CLI
            response = self.agent.handle_input(user_text)
            
            # 2. Post process and chunk to pass Telegram message text constraints
            self._send_message(chat_id, response)
        except Exception as e:
            error_msg = f"[Kernel Error] {str(e)}"
            self.console.print(f"[red]{error_msg}[/red]")
            self._send_message(chat_id, error_msg)

    def _send_message(self, chat_id, text):
        """Sends a text message back to the user, chunking if necessary."""
        url = f"{self.api_url}/sendMessage"
        # Telegram max message length is 4096 characters
        max_length = 4000
        for i in range(0, len(text), max_length):
            chunk = text[i:i + max_length]
            payload = {"chat_id": chat_id, "text": chunk}
            try:
                response = requests.post(url, json=payload)
                response.raise_for_status()
            except Exception as e:
                self.console.print(f"[red]Failed to send message to user: {e}[/red]")

    def _send_chat_action(self, chat_id, action="typing"):
        """Sends a UI state (like 'typing...') to the chat."""
        url = f"{self.api_url}/sendChatAction"
        payload = {"chat_id": chat_id, "action": action}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass # Non-critical failure

    def _handle_telegram_audio(self, chat_id, file_id) -> str | None:
        """Downloads audio from Telegram, transcribes it, and returns the text."""
        self._send_chat_action(chat_id, "record_audio")
        
        try:
            # 1. Get file path from Telegram
            get_file_url = f"{self.api_url}/getFile"
            resp = requests.get(get_file_url, params={"file_id": file_id}, timeout=15)
            file_data = resp.json()
            if not file_data.get("ok"):
                self._send_message(chat_id, "❌ Erro ao obter link do arquivo de voz.")
                return None
            
            file_path = file_data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            
            # 2. Download to local tmp
            local_path = os.path.join("data", f"tg_voice_{uuid4().hex[:8]}.ogg")
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            audio_resp = requests.get(download_url, timeout=30)
            with open(local_path, "wb") as f:
                f.write(audio_resp.content)
            
            # 3. Transcribe via STT Tool
            from tools.registry import registry
            stt_tool = registry.get_tool("speech_to_text")
            if not stt_tool:
                self._send_message(chat_id, "⚠️ STT Tool não registrada no kernel.")
                return None
            
            self._send_chat_action(chat_id, "typing")
            result_json = stt_tool.execute(audio_path=local_path)
            res = json.loads(result_json)
            
            # Cleanup source audio
            if os.path.exists(local_path):
                os.remove(local_path)
                
            if "error" in res:
                self._send_message(chat_id, f"❌ Erro na transcrição: {res['error']}")
                return None
            
            transcription = res.get("text", "")
            if not transcription:
                self._send_message(chat_id, "🤔 Não consegui entender o áudio.")
                return None
            
            self._send_message(chat_id, f"🎙️ _Transcrição:_ \"{transcription}\"")
            return transcription
            
        except Exception as e:
            self.console.print(f"[red]Telegram Audio Error: {e}[/red]")
            self._send_message(chat_id, f"❌ Erro crítico ao processar áudio: {str(e)}")
            return None
