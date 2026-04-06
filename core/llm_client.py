from typing import Optional, List
import logging
from core.llm_router import router

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Wrapper for LLM requests. 
    Now delegates everything to LLMRouter for multi-provider support.
    """
    def __init__(self):
        # api_key handled via config_manager in LLMRouter
        pass

    def generate(self, system_prompt: str, user_prompt: str, task_hint: Optional[str] = None, images: Optional[List[str]] = None) -> str:
        """
        Sends a generation request via the central router with vision support.
        
        Args:
            system_prompt: Contexto do sistema para o LLM
            user_prompt: Entrada do usuário para geração
            task_hint: Dica opcional para guiar a geração
            images: Lista de URLs ou paths de imagens para multimodalidade
        
        Returns:
            String com o texto gerado pelo LLM
        
        Raises:
            RuntimeError: Se a requisição falhar
        """
        try:
            return router.generate(system_prompt, user_prompt, task_hint=task_hint, images=images)
        except Exception as e:
            logger.error(f"LLM geração falhou: {e}")
            raise RuntimeError(f"Falha ao gerar resposta LLM: {e}") from e