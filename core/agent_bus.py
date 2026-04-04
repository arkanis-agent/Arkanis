import time
import os
import json
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
        self.storage_path = "data/agent_bus.json"
        self.load_state()

    def load_state(self):
        """Loads historical messages and connections from disk."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.message_history = data.get("history", [])
                    self.connections = data.get("connections", [])
            except Exception as e:
                print(f"Error loading AgentBus state: {e}")

    def save_state(self):
        """Persists historical data to disk."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump({
                    "history": self.message_history,
                    "connections": self.connections
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving AgentBus state: {e}")

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
        self.save_state()

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
        self.save_state()
        
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
        self._record_connection(from_aid, "ALL")
        self.save_state()
        
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
        
        # Normalize system-level IDs to ensure graph compatibility
        f_aid = from_aid.upper() if from_aid.lower() in ["system", "all"] else from_aid
        t_aid = to_aid.upper() if to_aid.lower() in ["system", "all"] else to_aid
        
        conn = {
            "source": f_aid, 
            "target": t_aid, 
            "last_interaction": now_str,
            "last_interaction_ms": now_ts
        }
        
        for c in self.connections:
            if c["source"] == f_aid and c["target"] == t_aid:
                c["last_interaction"] = now_str
                c["last_interaction_ms"] = now_ts
                return
                
        self.connections.append(conn)
        if len(self.connections) > self.max_connections:
            self.connections.pop(0)

    def get_observability_data(self) -> Dict[str, Any]:
        """Returns the full state of all agents for the Control Center UI."""
        agent_data = []
        stats = {
            "total": len(self.agents),
            "active": 0,
            "idle": 0,
            "paused": 0,
            "errors": 0
        }
        
        for aid, instance in self.agents.items():
            status = getattr(instance, "status", "idle")
            
            # Update stats
            if status == "running" or status == "active":
                stats["active"] += 1
            elif status == "paused":
                stats["paused"] += 1
            elif status == "error":
                stats["errors"] += 1
            else:
                stats["idle"] += 1
                
            # Extract standard fields or use defaults
            agent_data.append({
                "id": aid,
                "role": getattr(instance, "role", "Worker Agent"),
                "status": status,
                "mode": getattr(instance, "mode", "MANUAL"),
                "cycle": getattr(instance, "current_cycle", 0), # Frontend expects 'cycle'
                "current_cycle": getattr(instance, "current_cycle", 0), # Keep both for safety
                "is_custom": getattr(instance, "is_custom", False),
                "last_seen": getattr(instance, "last_seen", datetime.now().strftime("%H:%M:%S")),
                "current_action": getattr(instance, "current_action", "Standby")
            })
        
        # Inject the central "ALL" hub node for the Neural Map so broadcasts have a valid target node
        graph_nodes = list(agent_data)
        graph_nodes.append({
            "id": "ALL",
            "role": "Agent Bus Multiplexer",
            "status": "running",
            "current_action": "Roteando conexões..."
        })
        
        # Inject the "SYSTEM" node for root-level events and registration message compatibility
        graph_nodes.append({
            "id": "SYSTEM",
            "role": "Arkanis Kernel",
            "status": "active",
            "current_action": "Gerenciando subsistemas..."
        })
        
        return {
            "agents": agent_data,
            "stats": stats, # REQUIRED by script.js
            "connections": self.connections,
            "graph": {
                "nodes": graph_nodes,
                "links": self.connections
            },
            "history": self.message_history[-30:] # Last 30 for quick view
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