import time
import os
import json
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import deque
import queue

class AgentBus:
    """
    ARKANIS AGENT BUS: The central nervous system for multi-agent communication.
    Handles message passing, status tracking, and observability for the Control Center.
    """
    def __init__(self):
        self.agents = {}
        self.message_history = deque(maxlen=500)
        self.connections = []
        self.max_connections = 100
        self.storage_path = self._get_absolute_storage_path()
        self.save_debounce_time = 30.0  # Save every 30 seconds
        self.last_auto_save = time.time()
        self._save_queue = queue.Queue()
        self._db_lock = threading.RLock()  # Thread-safe locking
        self._auto_save_thread = None
        self._should_stop_auto_save = False
        self.load_state()
        self._start_auto_save()

    def _get_absolute_storage_path(self):
        """Ensures storage path is absolute."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "..", "data", "agent_bus.json")

    def _start_auto_save(self):
        """Starts background thread for batch saving."""
        def auto_save_loop():
            while not self._should_stop_auto_save:
                try:
                    # Process queued save requests
                    while not self._save_queue.empty():
                        self.save_state()
                    # Periodic auto-save
                    if time.time() - self.last_auto_save > self.save_debounce_time:
                        self.save_state()
                        self.last_auto_save = time.time()
                    time.sleep(1)  # Check every second
                except Exception as e:
                    print(f"Error in auto-save thread: {e}")

        self._auto_save_thread = threading.Thread(target=auto_save_loop, daemon=True)
        self._auto_save_thread.start()

    def _request_save(self):
        """Queue a save request instead of immediate save."""
        self._save_queue.put(True)

    def load_state(self):
        """Loads historical messages and connections from disk."""
        if os.path.exists(self.storage_path):
            try:
                with self._db_lock:
                    with open(self.storage_path, "r") as f:
                        data = json.load(f)
                        self.message_history.clear()
                        self.message_history.extend(data.get("history", []))
                        self.connections = data.get("connections", [])
            except Exception as e:
                print(f"Error loading AgentBus state: {e}")
                self.message_history.clear()
                self.connections = []

    def save_state(self):
        """Persists historical data to disk with proper locking."""
        with self._db_lock:
            try:
                os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
                temp_path = self.storage_path + ".tmp"
                with open(temp_path, "w") as f:
                    json.dump({
                        "history": list(self.message_history),
                        "connections": self.connections
                    }, f, indent=2)
                os.replace(temp_path, self.storage_path)
                self.last_auto_save = time.time()
            except Exception as e:
                print(f"Error saving AgentBus state: {e}")

    def register_agent(self, agent_id: str, instance: Any):
        with self._db_lock:
            self.agents[agent_id] = instance
            self._record_history({
                "from": "SYSTEM",
                "to": "ALL",
                "type": "registration",
                "content": f"Agent '{agent_id}' registered to the bus.",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            self._request_save()

    def unregister_agent(self, agent_id: str):
        with self._db_lock:
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
        self._request_save()
        
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
        self._request_save()
        
        for aid, target in self.agents.items():
            if aid != from_aid and hasattr(target, "inbox"):
                target.inbox.append(msg)

    def _record_history(self, msg: Dict[str, Any]):
        """Thread-safe history recording."""
        with self._db_lock:
            self.message_history.append(msg)

    def _record_connection(self, from_aid: str, to_aid: str):
        """Track communication edges for the graph visualization."""
        now_ts = time.time_ns() // 1_000_000 
        now_str = datetime.now().strftime("%H:%M:%S")
        
        f_aid = from_aid.upper() if from_aid.lower() in ["system", "all"] else from_aid
        t_aid = to_aid.upper() if to_aid.lower() in ["system", "all"] else to_aid
        
        with self._db_lock:
            for c in self.connections:
                if c["source"] == f_aid and c["target"] == t_aid:
                    c["last_interaction"] = now_str
                    c["last_interaction_ms"] = now_ts
                    return
                    
            self.connections.append({
                "source": f_aid, 
                "target": t_aid, 
                "last_interaction": now_str,
                "last_interaction_ms": now_ts
            })
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
            
            if status in ["running", "active"]:
                stats["active"] += 1
            elif status == "paused":
                stats["paused"] += 1
            elif status == "error":
                stats["errors"] += 1
            else:
                stats["idle"] += 1
                
            agent_data.append({
                "id": aid,
                "role": getattr(instance, "role", "Worker Agent"),
                "status": status,
                "mode": getattr(instance, "mode", "MANUAL"),
                "cycle": getattr(instance, "current_cycle", 0),
                "is_custom": getattr(instance, "is_custom", False),
                "last_seen": getattr(instance, "last_seen", datetime.now().strftime("%H:%M:%S")),
                "current_action": getattr(instance, "current_action", "Standby")
            })
        
        graph_nodes = list(agent_data)
        graph_nodes.append({
            "id": "ALL",
            "role": "Agent Bus Multiplexer",
            "status": "running",
            "current_action": "Roteando conexões..."
        })
        
        graph_nodes.append({
            "id": "SYSTEM",
            "role": "Arkanis Kernel",
            "status": "active",
            "current_action": "Gerenciando subsistemas..."
        })
        
        with self._db_lock:
            baseline_links = self.connections[:]
            existing_pairs = set()
            
            for c in baseline_links:
                existing_pairs.add((c["source"], c["target"]))
                existing_pairs.add((c["target"], c["source"]))
                
            if ("SYSTEM", "ALL") not in existing_pairs:
                baseline_links.append({"source": "SYSTEM", "target": "ALL", "last_interaction": "Baseline", "last_interaction_ms": 0})
                existing_pairs.add(("SYSTEM", "ALL"))
                
            for aid in self.agents.keys():
                if (aid, "SYSTEM") not in existing_pairs:
                    baseline_links.append({"source": aid, "target": "SYSTEM", "last_interaction": "Baseline", "last_interaction_ms": 0})
                    existing_pairs.add((aid, "SYSTEM"))

        return {
            "agents": agent_data,
            "stats": stats,
            "connections": self.connections,
            "graph": {
                "nodes": graph_nodes,
                "links": baseline_links
            },
            "history": list(self.message_history)[-30:]
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

    def shutdown(self):
        """Properly shutdown the agent bus and perform final save."""
        self._should_stop_auto_save = True
        self.save_state()
        if self._auto_save_thread:
            self._auto_save_thread.join(timeout=5)

# Singleton instance
agent_bus = AgentBus()