"""
ARKANIS V3.1 — Custom Agent
A lightweight, user-configurable agent that can be created via the WebUI.
Inherits from ArkanisAgent but restricts tools and injects a custom role/persona.
"""
import threading
import time
import os
import re
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
        self.role = self._sanitize_input(role)
        self.persona = self._sanitize_input(persona)
        self.allowed_tools = allowed_tools or []
        self.current_action = "Idle"
        self._last_tools_check = time.time()
        self._filtered_tools_cache: str = ""

        # Override planner identity with persona if provided and planner exists
        if hasattr(self, 'planner') and persona:
            self.planner.agent_identity = (
                f"[ROLE: {self.role}]\n"
                f"[PERSONA]: {persona}\n\n"
                f"Você é um agente especializado do ecossistema ARKANIS. "
                f"Seu papel é: {self.role}. Siga as instruções da persona acima."
            )

    @staticmethod
    def _sanitize_input(text: str) -> str:
        """Sanitize user input to prevent injection attacks."""
        if not text:
            return ""
        # Remove potential command injection characters
        text = re.sub(r'[;|&$`]', '', text)
        return text.strip()[:500]  # Limit length for safety

    def _get_filtered_tools_description(self) -> str:
        """Return only the tools this agent is allowed to use with caching."""
        # Check if cache is valid (within 60 seconds)
        if self._filtered_tools_cache and (time.time() - self._last_tools_check) < 60:
            return self._filtered_tools_cache
        
        if not isinstance(self.allowed_tools, list) or not self.allowed_tools:
            # No restriction — all tools
            return ""
        
        all_tools = registry.list_tools()
        filtered = {}
        validated_tools = []
        
        for tool_name in self.allowed_tools:
            if tool_name in all_tools:
                filtered[tool_name] = all_tools[tool_name]
                validated_tools.append(tool_name)
            else:
                self._warn_unused_tool(tool_name)
        
        if not filtered:
            self._filtered_tools_cache = ""
            self._last_tools_check = time.time()
            return ""
        
        lines = [f"- {name}: {desc}" for name, desc in filtered.items()]
        self._filtered_tools_cache = "\n".join(lines)
        self._last_tools_check = time.time()
        return self._filtered_tools_cache

    def _warn_unused_tool(self, tool_name: str) -> None:
        """Log warning for non-existent tool."""
        import logging
        logging.warning(f"[CustomAgent {self.agent_id}] Tool '{tool_name}' not found in registry.")

    @classmethod
    def create(
        cls,
        agent_id: str,
        role: str,
        persona: str = "",
        allowed_tools: Optional[List[str]] = None,
    ) -> "CustomAgent":
        """Factory method to create, validate, and register a new custom agent."""
        agent_bus.validate_agent_id(agent_id)
        
        agent = cls(
            agent_id=agent_id,
            role=role,
            persona=persona,
            allowed_tools=allowed_tools,
        )
        
        # CRITICAL: Register the agent to make it functional
        agent_bus.register_agent(agent)
        
        return agent

    @classmethod
    def exists(cls, agent_id: str) -> bool:
        """Check if a custom agent with this ID already exists."""
        try:
            return agent_bus.get_agent(agent_id) is not None
        except Exception:
            return False

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
            "is_custom": self.is_custom,
        }