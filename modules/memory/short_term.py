from typing import List, Dict, Any, Optional, Deque
from datetime import datetime, timezone
from collections import deque
import html

class ShortTermMemory:
    """
    ARKANIS V3.1 - Enhanced Temporal Memory
    
    Manages session-level context with precise timestamping and efficient storage.
    
    Attributes:
        limit (int): Maximum number of interactions to store
        interactions (Deque[Dict]): Circular buffer storing recent interactions
    """
    def __init__(self, limit: int = 15):
        self._limit = limit
        # Use deque with maxlen for O(1) operations and automatic discard of oldest item
        self._interactions: Deque[Dict[str, Any]] = deque(maxlen=limit)

    @property
    def limit(self) -> int:
        """Get the current memory limit."""
        return self._limit

    def add_interaction(self, user_input: str, plan: Optional[List[Dict[str, Any]]], result: str):
        """
        Adds a complete interaction to history with timestamp.
        
        Args:
            user_input (str): The user's input message
            plan (Optional[List[Dict]]): The execution plan (if any)
            result (str): The final result/response
        """
        # Sanitize inputs to prevent XSS and injection attacks
        sanitized_input = html.escape(user_input)
        sanitized_result = html.escape(result)
        sanitized_plan = []
        if plan:
            for step in plan:
                sanitized_step = {key: html.escape(str(value)) if isinstance(value, str) else value
                                for key, value in step.items()}
                sanitized_plan.append(sanitized_step)

        interaction = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "user_input": sanitized_input,
            "plan": sanitized_plan or [],
            "result": sanitized_result
        }
        self._interactions.append(interaction)

    def get_context(self) -> str:
        """
        Returns the current history formatted as a temporal string for the LLM prompt.
        
        Returns:
            str: Formatted context string with interaction history
        """
        if not self._interactions:
            return "Nenhum histórico recente disponível nesta sessão."
        
        context_lines = ["Histórico de Interações:\n"]
        for i, interaction in enumerate(self._interactions, 1):
            context_lines.append(f"Interação {i} | {interaction['timestamp']}")
            context_lines.append(f"• Usuário: {interaction['user_input']}")
            
            # Smart Tool Summarizer
            if interaction['plan']:
                tools_used = [f"{step.get('tool', 'unknown')}" for step in interaction['plan']]
                context_lines.append(f"• Ferramentas: {', '.join(tools_used)}")
            
            # Content summary with truncation
            res = interaction['result']
            if len(res) > 300:
                res = res[:300] + "... [truncado]"
            context_lines.append(f"• Resposta: {res}\n")
        
        return "\n".join(context_lines)

    def clear(self):
        """Clears the session history."""
        self._interactions.clear()

    @property
    def interaction_count(self) -> int:
        """Returns the current number of stored interactions."""
        return len(self._interactions)

# Global instance for easy access
session_memory = ShortTermMemory(limit=15)