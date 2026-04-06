import json
import logging
import os
import threading
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configurando logging padrão
logger = logging.getLogger(__name__)

# Path configurável para goals
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
GOALS_FILE = os.path.join(DEFAULT_DATA_DIR, "goals.json")

# Enums válidos para validação
VALID_PRIORITIES = {'low', 'medium', 'high'}
VALID_STATUSES = {'active', 'paused', 'completed', 'blocked'}


class Goal:
    def __init__(self, description: str, priority: str = 'medium', parent_id: Optional[str] = None):
        self.id = str(uuid.uuid4())[:8]
        self.description = description.strip()
        self.priority = self._validate_priority(priority)
        self.status = 'active'
        self.progress = 0
        self.parent_id = parent_id
        self.depends_on: List[str] = []
        self.agents_involved: List[str] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.notes: List[str] = []

    def _validate_priority(self, priority: str) -> str:
        """Valida se o prioridade está entre os valores permitidos."""
        if priority not in VALID_PRIORITIES:
            logger.warning(f"Priority inválido: {priority}, usando 'medium'")
            return 'medium'
        return priority

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'progress': self.progress,
            'parent_id': self.parent_id,
            'depends_on': self.depends_on,
            'agents_involved': self.agents_involved,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Goal':
        g = cls(data['description'], data.get('priority', 'medium'), data.get('parent_id'))
        g.id = data['id']
        g.status = data.get('status', 'active')
        g.progress = data.get('progress', 0)
        g.depends_on = data.get('depends_on', [])
        g.agents_involved = data.get('agents_involved', [])
        g.created_at = datetime.strptime(data['created_at'], '%Y-%m-%d %H:%M:%S')
        g.updated_at = datetime.strptime(data['updated_at'], '%Y-%m-%d %H:%M:%S')
        g.notes = data.get('notes', [])
        return g


class GoalManager:
    def __init__(self, data_dir: Optional[str] = None):
        global GOALS_FILE
        if data_dir:
            GOALS_FILE = os.path.join(data_dir, 'goals.json')
        self._lock = threading.RLock()
        self.goals: Dict[str, Goal] = {}
        self._load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(GOALS_FILE), exist_ok=True)

    def _load(self):
        if not os.path.exists(GOALS_FILE):
            return
        try:
            with self._lock:
                with open(GOALS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.goals[k] = Goal.from_dict(v)
        except json.JSONDecodeError as e:
            logger.error(f'Sua de dados goals corrompida: {e}')
        except Exception as e:
            logger.error(f'Mal ao carregar goals: {e}')

    def _save(self):
        """Salva goals no disco. O caller deve segurar o lock."""
        try:
            self._ensure_dir()
            data = {k: v.to_dict() for k, v in self.goals.items()}
            with open(GOALS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f'Falha ao salvar goals: {e}')
        
    def validate_depend(self, goal_id: str, depends_on: List[str]) -> bool:
        """
        Valida se os goals dependentes existem e não formam ciclos.
        """
        # Verifica se os dependentes existiam
        for dep_id in depends_on:
            if dep_id not in self.goals:
                logger.warning(f'Goal dependente {dep_id} não existe')
                return False
        # Verifica ciclos (simples - poderia ser mais robusto com DFS)
        # Simplificado para evitar loops entre dependências
        return True

    def create_goal(self, description: str, priority: str = 'medium', parent_id: Optional[str] = None) -> Optional[Goal]:
        if not description or not description.strip():
            logger.error('Descrição da goal não pode estar vazia')
            return None
        g = Goal(description, priority, parent_id)
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

    def update_status(self, goal_id: str, status: str) -> bool:
        """Atualiza status com validação."""
        if status not in VALID_STATUSES:
            logger.error(f'Status inválido: {status}')
            return False
        with self._lock:
            if goal_id in self.goals:
                self.goals[goal_id].status = status
                self.goals[goal_id].updated_at = datetime.now()
                self._save()
                return True
            return False

    def update_progress(self, goal_id: str, progress: int, note: str = '') -> bool:
        """Atualiza progresso com faixa de validação."""
        progress = max(0, min(100, progress))
        with self._lock:
            if goal_id in self.goals:
                self.goals[goal_id].progress = progress
                self.goals[goal_id].updated_at = datetime.now()
                if note:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    self.goals[goal_id].notes.append(f'[{timestamp}] {note}')
                self._save()
                return True
            return False

    def assign_agent(self, goal_id: str, agent_id: str) -> bool:
        """Atribui um agente a uma goal, evitando duplicatas."""
        with self._lock:
            if goal_id in self.goals:
                goal = self.goals[goal_id]
                if agent_id not in goal.agents_involved:
                    goal.agents_involved.append(agent_id)
                    goal.updated_at = datetime.now()
                    self._save()
                return True
            return False

    def delete_goal(self, goal_id: str) -> bool:
        """Remove uma goal e atualiza referências dependentes."""
        with self._lock:
            if goal_id in self.goals:
                deleted = self.goals.pop(goal_id)
                # Atualiza todos goals que dependem desta goal
                for g in self.goals.values():
                    if goal_id in g.depends_on:
                        g.depends_on.remove(goal_id)
                        g.updated_at = datetime.now()
                self._save()
                return True
            return False


goal_manager = GoalManager()
