import threading
from typing import Dict, List, Any, Optional
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

    def get_agent(self, agent_id: str) -> Optional[Any]:
        with self._lock:
            return self._agents.get(agent_id)

    def list_agent_ids(self) -> List[str]:
        with self._lock:
            return list(self._agents.keys())

    def pause_agent(self, agent_id: str) -> bool:
        """Signal an agent to pause between cycles."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent and hasattr(agent, "pause_requested"):
                agent.status = "paused"
                agent.pause_requested.set()
                return True
            return False

    def resume_agent(self, agent_id: str) -> bool:
        """Signal a paused agent to resume."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent and hasattr(agent, "pause_requested"):
                agent.status = "idle"
                agent.pause_requested.clear()
                if hasattr(agent, "resume_requested"):
                    agent.resume_requested.set()
                return True
            return False

    def stop_agent(self, agent_id: str) -> bool:
        """Signal an agent to stop and unregister it (only for custom agents)."""
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False
            # Signal stop if possible
            if hasattr(agent, "stop_requested"):
                agent.stop_requested.set()
            if hasattr(agent, "pause_requested"):
                agent.resume_requested.set()  # Unblock if paused
            # Only remove non-core agents from registry
            if getattr(agent, "is_custom", False):
                del self._agents[agent_id]
            else:
                agent.status = "idle"
            return True

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

    def get_agent_detail(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Return full detail snapshot of a single agent for the Control Center."""
        with self._lock:
            instance = self._agents.get(agent_id)
            if not instance:
                return None
            return self._build_agent_snapshot(agent_id, instance)

    def _build_agent_snapshot(self, aid: str, instance: Any) -> Dict[str, Any]:
        """Build a rich status snapshot from any agent instance."""
        status = getattr(instance, "status", "idle")
        recent_logs = getattr(instance, "logs", [])
        # Return only last 5 log entries for the card mini-feed
        mini_logs = recent_logs[-5:] if recent_logs else []

        return {
            "id": aid,
            "status": status.lower() if isinstance(status, str) else "idle",
            "mode": getattr(instance, "mode", "manual").upper(),
            "cycle": getattr(instance, "current_cycle", 0),
            "current_action": getattr(instance, "current_action", "Idle"),
            "role": getattr(instance, "role", "Agente Principal"),
            "allowed_tools": getattr(instance, "allowed_tools", []),
            "is_custom": getattr(instance, "is_custom", False),
            "logs": mini_logs,
            "last_seen": datetime.now().strftime("%H:%M:%S"),
        }

    def get_observability_data(self) -> Dict[str, Any]:
        """Provides a real-time snapshot of the system state for the WebUI."""
        with self._lock:
            agents_snapshot = [
                self._build_agent_snapshot(aid, inst)
                for aid, inst in self._agents.items()
            ]

            return {
                "agents": agents_snapshot,
                "history": self.message_history[-20:],
                "stats": {
                    "total": len(agents_snapshot),
                    "active": len([a for a in agents_snapshot if a["status"] == "running"]),
                    "idle": len([a for a in agents_snapshot if a["status"] == "idle"]),
                    "paused": len([a for a in agents_snapshot if a["status"] == "paused"]),
                    "errors": len([a for a in agents_snapshot if a["status"] == "error"]),
                }
            }


# Singleton global instance
agent_bus = AgentBus()
