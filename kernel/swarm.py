from typing import List, Dict, Any, Optional
import threading
import uuid
from core.agent_bus import agent_bus
from core.llm_client import LLMClient
from core.logger import logger

class SwarmWorker:
    """A temporary specialized agent spawned by the Hive."""
    def __init__(self, role: str, goal: str, parent_id: str = "main"):
        self.id = f"worker_{role.lower().replace(' ', '_')}_{str(uuid.uuid4())[:4]}"
        self.role = role
        self.goal = goal
        self.parent_id = parent_id
        self.status = "idle"
        self.mode = "AUTO"
        self.current_action = "Inicializando..."
        self.is_custom = True # Mark as custom to allow auto-cleanup
        self.logs = []
        
        # Register in bus
        agent_bus.register_agent(self.id, self)
        logger.info(f"[Hive] Novo worker spawned: {self.id} ({self.role})")

    def run(self):
        """Execute the worker's dedicated task."""
        self.status = "running"
        self.current_action = f"Trabalhando em: {self.goal[:30]}..."
        
        system_prompt = f"Você é o agente especialista {self.role}. Seu objetivo único é: {self.goal}. Responda de forma técnica e direta."
        user_prompt = f"Execute sua tarefa agora no contexto de Arkanis V4."
        
        llm = LLMClient()
        # In a real swarm, this would call tools. For now, simulate high-level task execution.
        result = llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        
        self.logs.append({"time": "now", "type": "success", "message": "Tarefa concluída."})
        self.status = "idle"
        self.current_action = "Concluído. Aguardando recall."
        
        # Notify parent via bus
        agent_bus.send_message(self.id, self.parent_id, f"WORKER_DONE:{self.id}: {result}")

class SwarmManager:
    """Orchestrator for the Hive Swarm."""
    def __init__(self):
        self.active_workers: List[SwarmWorker] = []

    def delegate_project(self, project_goal: str, sub_tasks: List[Dict[str, str]]):
        """Spawns workers for each sub-task."""
        logger.info(f"[Hive] Delegando projeto complexo para {len(sub_tasks)} workers.")
        
        for task in sub_tasks:
            worker = SwarmWorker(role=task['role'], goal=task['goal'])
            self.active_workers.append(worker)
            # Run each worker in a separate thread for parallel execution
            threading.Thread(target=worker.run, daemon=True).start()

    def cleanup(self):
        """Removes finished workers from the bus."""
        for worker in self.active_workers:
            if worker.status == "idle":
                agent_bus.unregister_agent(worker.id)
        self.active_workers = [w for w in self.active_workers if w.status != "idle"]

swarm_manager = SwarmManager()
