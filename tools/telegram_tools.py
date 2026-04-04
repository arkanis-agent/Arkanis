import os
import json
import requests
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

class TelegramMessageTool(BaseTool):
    @property
    def name(self) -> str:
        return "send_telegram_notification"

    @property
    def description(self) -> str:
        return (
            "INTEGRAÇÃO OFICIAL COM TELEGRAM. Envia uma mensagem de texto ao usuário no Telegram. "
            "Use isso quando você estiver trabalhando em background/continuous tasks e "
            "precisar notificar o usuário ativamente sobre novas descobertas ou erros críticos. "
            "Sempre que o usuário pedir para 'mandar no telegram' ou 'enviar notificação', use esta ferramenta."
        )

    @property
    def arguments(self) -> dict:
        return {
            "message": "Texto em português para enviar na notificação do Telegram (suporta emojis)."
        }

    def execute(self, **kwargs) -> str:
        message = kwargs.get("message")
        if not message:
            return json.dumps({"error": "Parâmetro 'message' é obrigatório."})
            
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return json.dumps({"error": "Nenhum TELEGRAM_BOT_TOKEN configurado no sistema. A integração está desativada."})
            
        chat_id = os.getenv("TELEGRAM_ADMIN_ID")
        if not chat_id:
            logger.warning("TELEGRAM_ADMIN_ID não definido. Sugira ao usuário enviar 'olá' ao bot no celular para parear a ID.")
            return json.dumps({"error": "TELEGRAM_ADMIN_ID não está configurado. O usuário precisa mandar uma mensagem no Telegram para o bot primeiro para que o sistema capture seu Chat ID temporariamente."})
            
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info(f"Telegram notification sent to {chat_id}.", source="telegram_tool")
            return json.dumps({"success": True, "info": "Mensagem enviada com sucesso ao Telegram do usuário."})
        except Exception as e:
            logger.error(f"Failed to send telegram notification: {e}")
            return json.dumps({"error": f"Falha de rede ao enviar para a API do Telegram: {e}"})

registry.register(TelegramMessageTool())
