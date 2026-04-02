"""
ARKANIS V3.1 — Custom Agent
A lightweight, user-configurable agent that can be created via the WebUI.
Inherits from ArkanisAgent but restricts tools and injects a custom role/persona.
"""
import threading
import time
import os
from typing import List, Optional
from kernel.agent import ArkanisAgent
from core.agent_bus import agent_bus
from tools.registry import registry


class CustomAgent(ArkanisAgent):
    """
    A specializable agent created at runtime via the Control Center.
    
    Key differences from ArkanisAgent:
    - is_custom = True (can be stopped/removed from the bus)
    - role: descriptive role like "Pesquisador Web"
    - persona: injected into the planner's system prompt
    - allowed_tools: restricts which tools the planner can use
    """

    def __init__(
        self,
        agent_id: str,
        role: str = "Agente Personalizado",
        persona: str = "",
        allowed_tools: Optional[List[str]] = None,
    ):
        # Init base agent with custom ID (skips re-registering virtual sub-agents)
        super().__init__(agent_id=agent_id)
        
        # Custom flags
        self.is_custom = True
        self.role = role
        self.persona = persona
        self.allowed_tools = allowed_tools or []
        self.current_action = "Idle"

        # Override planner identity with persona if provided
        if persona:
            self.planner.agent_identity = (
                f"[ROLE: {role}]\n"
                f"[PERSONA]: {persona}\n\n"
                f"Você é um agente especializado do ecossistema ARKANIS. "
                f"Seu papel é: {role}. Siga as instruções da persona acima."
            )

    def _get_filtered_tools_description(self) -> str:
        """Return only the tools this agent is allowed to use."""
        if not self.allowed_tools:
            # No restriction — all tools
            return ""
        
        all_tools = registry.list_tools()
        filtered = {k: v for k, v in all_tools.items() if k in self.allowed_tools}
        if not filtered:
            return ""
        
        lines = [f"- {name}: {desc}" for name, desc in filtered.items()]
        return "\n".join(lines)

    @classmethod
    def create(
        cls,
        agent_id: str,
        role: str,
        persona: str = "",
        allowed_tools: Optional[List[str]] = None,
    ) -> "CustomAgent":
        """Factory method to create and register a new custom agent."""
        # Prevent duplicate IDs
        if agent_bus.get_agent(agent_id):
            raise ValueError(f"Agente com ID '{agent_id}' já existe.")

        agent = cls(
            agent_id=agent_id,
            role=role,
            persona=persona,
            allowed_tools=allowed_tools,
        )
        return agent

    def to_dict(self) -> dict:
        """Serialize for API responses."""
        return {
            "id": self.id,
            "role": self.role,
            "persona": self.persona,
            "allowed_tools": self.allowed_tools,
            "status": self.status,
            "mode": self.mode,
            "current_action": self.current_action,
            "is_custom": True,
        }
