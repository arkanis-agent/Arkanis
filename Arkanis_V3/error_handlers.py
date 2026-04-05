import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Armazenar padrões de chaves sensíveis em conjunto congelado
SENSITIVE_KEYS_FILTER = frozenset({'password', 'token', 'secret', 'api_key', 'auth', 'chave', 'senha', 'access_token'})


class ErrorHandler:
    @staticmethod
    def _sanitize_context(context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Filtra dados sensíveis do contexto para evitar vazamento em logs.
        
        Args:
            context: Dicionário contendo o contexto a ser sanitizado
        
        Returns:
            Dicionário com valores sensíveis mascarados ou None se contexto vazio
        """
        if not context:
            return None
        
        # Armazenar chave em lowercase para evitar múltiplas chamadas
        return {
            k: '***REDACTED***' if any(s in (lower_key := k.lower()) for s in SENSITIVE_KEYS_FILTER)\n            else v for k, v in context.items()
        }

    @staticmethod
    def critical_error(err: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Tratamento e registro estruturado de erros críticos.
        
        Args:
            err: Exceção capturada
            context: Contexto adicional para registro do erro (opcional)
        """
        # Saneamento de segurança antes do logging
        safe_ctx = ErrorHandler._sanitize_context(context)
        
        ctx_info = f" | Contexto: {safe_ctx}" if safe_ctx else ""
        logger.critical(
            "ERRO CRÍTICO DETECTADO: %s%s",
            err, ctx_info,
            exc_info=(type(err), err, err.__traceback__)
        )