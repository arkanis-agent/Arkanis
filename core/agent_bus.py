import time
from datetime import datetime
from typing import Dict, Any, List, Optional

class AgentBus:
    """
    ARKANIS AGENT BUS: The central nervous system for multi-agent communication.
    Handles message passing, status tracking, and observability for the Control Center.
    """
    def __init__(self):
        self.agents = {}
        self.message_history = []
        self.connections = []
        self.max_history = 500
        self.max_connections = 100

    def register_agent(self, agent_id: str, instance: Any):
        self.agents[agent_id] = instance
        # Record registration as a system message
        self._record_history({
            "from": "SYSTEM",
            "to": "ALL",
            "type": "registration",
            "content": f"Agent '{agent_id}' registered to the bus.",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

    def unregister_agent(self, agent_id: str):
        if agent_id in self.agents:
            del self.agents[agent_id]

    def get_agent(self, agent_id: str) -> Optional[Any]:
        return self.agents.get(agent_id)

    def send_message(self, from_aid: str, to_aid: str, content: str):
        """Direct message between agents."""
        msg = {
            "from": from_aid,
            "to": to_aid,
            "type": "direct",
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        self._record_history(msg)
        self._record_connection(from_aid, to_aid)
        
        target = self.agents.get(to_aid)
        if target and hasattr(target, "inbox"):
            target.inbox.append(msg)

    def broadcast_message(self, from_aid: str, content: str):
        """Message to all registered agents."""
        msg = {
            "from": from_aid,
            "to": "ALL",
            "type": "broadcast",
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        self._record_history(msg)
        
        for aid, target in self.agents.items():
            if aid != from_aid and hasattr(target, "inbox"):
                target.inbox.append(msg)

    def _record_history(self, msg: Dict[str, Any]):
        self.message_history.append(msg)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

    def _record_connection(self, from_aid: str, to_aid: str):
        """Track communication edges for the graph visualization."""
        now_ts = time.time_ns() // 1_000_000 
        now_str = datetime.now().strftime("%H:%M:%S")
        
        conn = {
            "source": from_aid, 
            "target": to_aid, 
            "last_interaction": now_str,
            "last_interaction_ms": now_ts
        }
        
        for c in self.connections:
            if c["source"] == from_aid and c["target"] == to_aid:
                c["last_interaction"] = now_str
                c["last_interaction_ms"] = now_ts
                return
                
        self.connections.append(conn)
        if len(self.connections) > self.max_connections:
            self.connections.pop(0)

    def get_observability_data(self) -> Dict[str, Any]:
        """Returns the full state of all agents for the Control Center UI."""
        agent_data = []
        for aid, instance in self.agents.items():
            # Extract standard fields or use defaults
            agent_data.append({
                "id": aid,
                "role": getattr(instance, "role", "Worker Agent"),
                "status": getattr(instance, "status", "idle"),
                "mode": getattr(instance, "mode", "MANUAL"),
                "current_cycle": getattr(instance, "current_cycle", 0),
                "is_custom": getattr(instance, "is_custom", False)
            })
        
        return {
            "agents": agent_data,
            "connections": self.connections,
            "history": self.message_history[-20:] # Last 20 for quick view
        }

    def pause_agent(self, agent_id: str) -> bool:
        agent = self.agents.get(agent_id)
        if agent and hasattr(agent, "pause_requested"):
            agent.pause_requested.set()
            return True
        return False

    def resume_agent(self, agent_id: str) -> bool:
        agent = self.agents.get(agent_id)
        if agent and hasattr(agent, "resume_requested"):
            agent.resume_requested.set()
            agent.pause_requested.clear()
            return True
        return False

    def stop_agent(self, agent_id: str) -> bool:
        agent = self.agents.get(agent_id)
        if agent:
            if hasattr(agent, "stop_requested"):
                agent.stop_requested.set()
            if hasattr(agent, "stop_loop"):
                agent.stop_loop()
            return True
        return False

    def get_agent_detail(self, agent_id: str) -> Optional[Dict]:
        agent = self.agents.get(agent_id)
        if not agent: return None
        return {
            "id": agent_id,
            "logs": getattr(agent, "logs", [])
        }

# Singleton instance
agent_bus = AgentBus()