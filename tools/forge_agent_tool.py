import json
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

class ForgeAgentTool(BaseTool):
    @property
    def name(self) -> str: return "forge_agent"
    
    @property
    def description(self) -> str: 
        return "Proposes the creation of a new autonomous sub-agent with specific tools and persona to solve complex tasks. Use this when the user needs a specialist."
        
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "agent_id": "A short, underscores-only ID for the agent (e.g. 'sports_analyst')",
            "role": "The professional title or role of the agent (e.g. 'Sports Data Analyst')",
            "persona": "Detailed instructions on how the agent should behave and process information.",
            "permissions": "Comma-separated list of tools the agent should have access to (e.g. 'web_search, fetch_url')."
        }
        
    def execute(self, **kwargs) -> str:
        agent_id = kwargs.get("agent_id", "").strip()
        role = kwargs.get("role", "").strip()
        persona = kwargs.get("persona", "").strip()
        permissions = kwargs.get("permissions", "").strip()
        
        if not agent_id or not role or not persona:
            return "Error: agent_id, role, and persona are required."
            
        proposed_agent = {
            "agent_id": agent_id,
            "role": role,
            "persona": persona,
            "permissions": [p.strip() for p in permissions.split(",") if p.strip()]
        }
        
        # Return a specific structured response that the UI/Planner can intercept.
        return f"FORGE_REQUEST:{json.dumps(proposed_agent)}"

# Safe tool registration
try:
    registry.register(ForgeAgentTool())
except Exception as e:
    logger.error(f"ForgeAgent tool registration failed: {e}")

def __register_tools__():
    """Called by the lazy loader in registry.py when forge_agent is first requested."""
    try:
        registry.register(ForgeAgentTool())
    except Exception as e:
        logger.error(f"ForgeAgent lazy registration failed: {e}")

__all__ = ["ForgeAgentTool"]

