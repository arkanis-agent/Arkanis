from typing import List, Dict, Any, Optional
from datetime import datetime

class ShortTermMemory:
    """
    ARKANIS V3.1 - Enhanced Temporal Memory
    Manages session-level context with precise timestamping for each interaction.
    """
    def __init__(self, limit: int = 15):
        self.limit = limit
        self.interactions: List[Dict[str, Any]] = []

    def add_interaction(self, user_input: str, plan: Optional[List[Dict[str, Any]]], result: str):
        """Adds a complete interaction to history with timestamp."""
        now = datetime.now()
        self.interactions.append({
            "timestamp": now.strftime("%H:%M:%S"),
            "user_input": user_input,
            "plan": plan if plan else [],
            "result": result
        })
        if len(self.interactions) > self.limit:
            self.interactions.pop(0)

    def get_context(self) -> str:
        """Returns the current history formatted as a temporal string for the LLM prompt."""
        if not self.interactions:
            return "Nenhum histórico recente disponível nesta sessão."
            
        context_lines = []
        for i, interaction in enumerate(self.interactions, 1):
            ts = interaction.get('timestamp', '--:--:--')
            context_lines.append(f"[T:{ts}] Usuário: {interaction['user_input']}")
            
            # Smart Tool Summarizer
            tools_used = [step.get('tool', 'unknown') for step in interaction['plan']]
            if tools_used:
                context_lines.append(f"-> Ações Arkanis: {', '.join(tools_used)}")
            
            # Content summary (limit result per interaction to save tokens if it's long)
            res = interaction['result']
            if len(res) > 300:
                res = res[:300] + "..."
            context_lines.append(f"-> Resposta: {res}\n")
        
        return "\n".join(context_lines).strip()

    def clear(self):
        """Clears the session history."""
        self.interactions = []

# Global instance for easy access
session_memory = ShortTermMemory(limit=15)
