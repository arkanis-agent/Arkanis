from tools.base_tool import BaseTool
from kernel.swarm import swarm_manager
from core.logger import logger
import json

class HiveDelegateTool(BaseTool):
    """
    HIVE_DELEGATE TOOL (Arkanis V4 Alpha)
    Spawns an autonomous swarm of specialized agents to handle a complex project.
    Use this when a task is too big for a single agent (e.g. 'Build a website with backend, frontend and tests').
    """
    def __init__(self):
        super().__init__(
            name="hive_delegate",
            description="Delega um projeto complexo para um enxame de agentes especializados (The Hive).",
            parameters={
                "project_goal": "O objetivo macro do projeto.",
                "sub_tasks": "Uma lista de tarefas JSON: [{'role': 'Engenheiro Backend', 'goal': 'Crie a API...'}, ...]"
            }
        )

    def execute(self, project_goal: str, sub_tasks: Any) -> str:
        try:
            # Handle string or list input
            if isinstance(sub_tasks, str):
                tasks_list = json.loads(sub_tasks)
            else:
                tasks_list = sub_tasks
                
            logger.info(f"[Hive] Desenhando enxame para: {project_goal}")
            swarm_manager.delegate_project(project_goal, tasks_list)
            
            return f"PROJETO DELEGADO AO THE HIVE: {len(tasks_list)} agentes em operação."
        except Exception as e:
            logger.error(f"[Hive] Erro ao delegar enxame: {e}")
            return f"FALHA NA DELEGAÇÃO: {str(e)}"

# Auto-registry in the project ecosystem
from tools.registry import registry
from typing import Any
registry.register(HiveDelegateTool())
