import threading
from typing import Dict, List, Any
from datetime import datetime

class AgentBus:
    def __init__(self):
        self._agents: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self.message_history: List[Dict[str, Any]] = []
        self.max_history = 500

    def register_agent(self, agent_id: str, agent_instance: Any):
        with self._lock:
            self._agents[agent_id] = agent_instance

    def unregister_agent(self, agent_id: str):
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]

    def send_message(self, from_agent: str, to_agent: str, content: str) -> bool:
        with self._lock:
            if to_agent in self._agents:
                target = self._agents[to_agent]
                msg = {
                    "id": len(self.message_history),
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "from": from_agent,
                    "to": to_agent,
                    "content": content,
                    "type": "direct"
                }
                # Add to agent's inbox
                if hasattr(target, "inbox"):
                    target.inbox.append(msg)
                    
                self._record_history(msg)
                return True
            return False

    def broadcast_message(self, from_agent: str, content: str):
        with self._lock:
            msg = {
                "id": len(self.message_history),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "from": from_agent,
                "to": "ALL",
                "content": content,
                "type": "broadcast"
            }
            for aid, target in self._agents.items():
                if aid != from_agent and hasattr(target, "inbox"):
                    target.inbox.append(msg)
                    
            self._record_history(msg)

    def _record_history(self, msg: Dict[str, Any]):
        self.message_history.append(msg)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

    def get_observability_data(self) -> Dict[str, Any]:
        """Provides a real-time snapshot of the system state for the WebUI."""
        with self._lock:
            agents_snapshot = []
            for aid, instance in self._agents.items():
                # Extract relevant metadata from the agent instance
                state = {
                    "id": aid,
                    "status": getattr(instance, "status", "idle").lower(),
                    "mode": getattr(instance, "mode", "manual").upper(),
                    "cycle": getattr(instance, "current_cycle", 0),
                    "last_seen": datetime.now().strftime("%H:%M:%S") # Placeholder for activity
                }
                agents_snapshot.append(state)
            
            return {
                "agents": agents_snapshot,
                "history": self.message_history[-20:], # Only latest 20 for UI
                "stats": {
                    "total": len(agents_snapshot),
                    "active": len([a for a in agents_snapshot if a["status"] != "idle"]),
                    "idle": len([a for a in agents_snapshot if a["status"] == "idle"]),
                    "errors": 0 # Placeholder for future health checks
                }
            }

# Singleton global instance
agent_bus = AgentBus()
