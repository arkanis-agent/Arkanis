from typing import List, Dict, Any

class ShortTermMemory:
    """
    Manages session-level context for the Arkanis agent.
    Keeps track of structural interactions: Input, Plan, and Result.
    """
    def __init__(self, limit: int = 10):
        self.limit = limit
        self.interactions: List[Dict[str, Any]] = []

    def add_interaction(self, user_input: str, plan: List[Dict[str, Any]], result: str):
        """Adds a complete interaction to history."""
        self.interactions.append({
            "user_input": user_input,
            "plan": plan,
            "result": result
        })
        if len(self.interactions) > self.limit:
            self.interactions.pop(0)

    def get_context(self) -> str:
        """Returns the current history formatted as a string for the LLM prompt."""
        if not self.interactions:
            return "Nenhum histórico recente."
            
        context_lines = []
        for i, interaction in enumerate(self.interactions, 1):
            context_lines.append(f"[Interação Anterior {i}]")
            context_lines.append(f"-> Usuário: {interaction['user_input']}")
            # Extract just the tools used to avoid huge JSON strings consuming context token limits
            tools_used = [step.get('tool', 'unknown') for step in interaction['plan']]
            context_lines.append(f"-> Ferramentas do Agente: {tools_used}")
            context_lines.append(f"-> Resultado: {interaction['result']}\n")
        
        return "\n".join(context_lines).strip()

    def clear(self):
        """Clears the history."""
        self.interactions = []

# Global instance for easy access
session_memory = ShortTermMemory(limit=10)
