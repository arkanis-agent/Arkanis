import json
import os
import threading
import uuid
from typing import Dict, List, Any
from datetime import datetime

GOALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "goals.json")

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

class Goal:
    def __init__(self, description: str, priority: str = "medium", parent_id: Optional[str] = None):
        self.id = str(uuid.uuid4())[:8]
        self.description = description
        self.priority = priority # low, medium, high
        self.status = "active" # active, paused, completed, blocked
        self.progress = 0 # 0 to 100
        self.parent_id = parent_id # For sub-goals
        self.depends_on: List[str] = [] # List of Goal IDs that must be completed first
        self.agents_involved: List[str] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.notes: List[str] = []

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "progress": self.progress,
            "parent_id": self.parent_id,
            "depends_on": self.depends_on,
            "agents_involved": self.agents_involved,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: dict):
        g = cls(data["description"], data.get("priority", "medium"), data.get("parent_id"))
        g.id = data["id"]
        g.status = data.get("status", "active")
        g.progress = data.get("progress", 0)
        g.depends_on = data.get("depends_on", [])
        g.agents_involved = data.get("agents_involved", [])
        g.created_at = datetime.strptime(data["created_at"], "%Y-%m-%d %H:%M:%S")
        g.updated_at = datetime.strptime(data["updated_at"], "%Y-%m-%d %H:%M:%S")
        g.notes = data.get("notes", [])
        return g

class GoalManager:
    """
    Sistema de Gerenciamento de Objetivos Globais.
    Coordena múltiplos agentes sob uma mesma diretriz de longo prazo.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.goals: Dict[str, Goal] = {}
        self._load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(GOALS_FILE), exist_ok=True)

    def _load(self):
        with self._lock:
            if os.path.exists(GOALS_FILE):
                try:
                    with open(GOALS_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for k, v in data.items():
                            self.goals[k] = Goal.from_dict(v)
                except Exception as e:
                    print(f"[GoalManager] Falha ao carregar goals: {e}")

    def _save(self):
        self._ensure_dir()
        with self._lock:
            try:
                data = {k: v.to_dict() for k, v in self.goals.items()}
                with open(GOALS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"[GoalManager] Falha ao salvar goals: {e}")

    def create_goal(self, description: str, priority: str = "medium", parent_id: Optional[str] = None) -> Goal:
        g = Goal(description, priority, parent_id)
        # If parent exists, we could theoretically add logic to link them back
        # but for now, the parent_id in the child is enough for filtering.
        with self._lock:
            self.goals[g.id] = g
        self._save()
        return g

    def list_goals(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [g.to_dict() for g in self.goals.values()]

    def get_subgoals(self, parent_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [g.to_dict() for g in self.goals.values() if g.parent_id == parent_id]

    def update_status(self, goal_id: str, status: str):
        with self._lock:
            if goal_id in self.goals:
                self.goals[goal_id].status = status
                self.goals[goal_id].updated_at = datetime.now()
        self._save()

    def update_progress(self, goal_id: str, progress: int, note: str = ""):
        with self._lock:
            if goal_id in self.goals:
                self.goals[goal_id].progress = max(0, min(100, progress))
                self.goals[goal_id].updated_at = datetime.now()
                if note:
                    self.goals[goal_id].notes.append(f"[{datetime.now().strftime('%H:%M:%S')}] {note}")
        self._save()

    def assign_agent(self, goal_id: str, agent_id: str):
        with self._lock:
            if goal_id in self.goals:
                if agent_id not in self.goals[goal_id].agents_involved:
                    self.goals[goal_id].agents_involved.append(agent_id)
                    self.goals[goal_id].updated_at = datetime.now()
        self._save()

goal_manager = GoalManager()
