import os
import json
import requests
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger


API_URL = "https://api.telegram.org"
MESSAGE_MAX_LENGTH = 4096


class TelegramMessageTool(BaseTool):
    @property
    def name(self) -> str:
        return "send_telegram_notification"

    @property
    def description(self) -> str:
        return (
            "INTEGRAÇÃO OFICIAL COM TELEGRAM. Envia uma mensagem de texto ao usuário no Telegram. "
            "Use isso quando estiver trabalhando em background/continuous tasks e "
            "precisar notificar o usuário ativamente sobre novas descobertas ou erros críticos. "
            "Sempre que o usuário pedir para 'mandar no telegram' ou 'enviar notificação', use esta ferramenta."
        )

    @property
    def arguments(self) -> dict:
        return {
            "message": "Texto em português para enviar na notificação do Telegram (suporta emojis)."
        }

    def _get_rate_limit_delay(self, response) -> float:
        """Retorna delay se estiver rate-limited, 0 caso contrário."""
        try:
            result = response.json()
            if result.get("ok") is False:
                error_code = result.get("error_code", 0)
                if error_code == 429:
                    return result.get("parameters", {}).get("retry_after", 5)
        except (json.JSONDecodeError, KeyError):
            pass
        return 0

    def _should_log_user_error(self, error_type: str) -> str:
        """Retorna mensagem genérica para não expor detalhes internos."""
        messages = {
            "network": "Não foi possível conectar ao serviço de mensagens.",
            "config": "A integração de Notificações não está configurada no sistema.",
            "content": "O conteúdo da mensagem excede o limite permitido pelo Telegram.",
            "api": "Falha ao processar a solicitação no Telegram.",
        }
        return messages.get(error_type, "Ocorreu um erro ao enviar a mensagem.")

    def execute(self, **kwargs) -> str:
        message = kwargs.get("message", "")
        if not message:
            logger.warning("Message parameter missing in TelegramMessageTool.execute()")
            return json.dumps({"error": "Parâmetro 'message' é obrigatório."})

        if len(message) > MESSAGE_MAX_LENGTH:
            logger.warning(
                f"Message too long: {len(message)} chars > {MESSAGE_MAX_LENGTH} limit. "
                f"Truncated to {MESSAGE_MAX_LENGTH} chars."
            )
            message = message[:MESSAGE_MAX_LENGTH]

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return json.dumps({"error": self._should_log_user_error("config")})

        chat_id = os.getenv("TELEGRAM_ADMIN_ID")
        if not chat_id:
            logger.warning(
                "TELEGRAM_ADMIN_ID não definido. O usuário precisa enviar 'olá' "
                "ao bot no celular primeiro para parear a ID."
            )
            return json.dumps({"error": self._should_log_user_error("config")})

        url = f"{API_URL}/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}

        session = requests.Session()
        try:
            resp = session.post(url, json=payload, timeout=10)

            retry_after = self._get_rate_limit_delay(resp)
            if retry_after > 0:
                logger.warning(f"Rate limit detected. Waiting {retry_after} seconds.")
                raise requests.exceptions.TooManyRequests(f"Rate limit. Try after {retry_after}s")

            resp.raise_for_status()
            logger.info(f"Telegram notification sent to {chat_id}.", source="telegram_tool")
            return json.dumps(
                {"success": True, "info": "Mensagem enviada com sucesso ao Telegram do usuário."}
            )
        except requests.exceptions.Timeout:
            logger.error("Telegram request timed out", extra={"source": "telegram_tool"})
            return json.dumps({"error": self._should_log_user_error("network")})
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed to send telegram notification: {e}")
            return json.dumps({"error": self._should_log_user_error("network")})
        except Exception as e:
            logger.error(f"Unexpected error in TelegramMessageTool: {e}", extra={"source": "telegram_tool"})
            return json.dumps({"error": self._should_log_user_error("api")})


registry.register(TelegramMessageTool())