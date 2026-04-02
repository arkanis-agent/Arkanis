from typing import Optional
from core.llm_router import router

class LLMClient:
    """
    Wrapper for LLM requests. 
    Now delegates everything to LLMRouter for multi-provider support.
    """
    def __init__(self, api_key: Optional[str] = None):
        # We ignore api_key here because LLMRouter handles it via config_manager
        pass

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a generation request via the central router.
        """
        return router.generate(system_prompt, user_prompt)
