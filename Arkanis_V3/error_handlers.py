import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class ErrorHandler:
    @staticmethod
    def critical_error(err: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Tratamento e registro estruturado de erros críticos."""
        ctx_info = f" | Contexto: {context}" if context else ""
        logger.critical(
            "ERRO CRÍTICO DETECTADO: %s%s",
            err, ctx_info,
            exc_info=(type(err), err, err.__traceback__)
        )
        # Integrar notificações (email/webhook) ou rotinas de recovery aqui