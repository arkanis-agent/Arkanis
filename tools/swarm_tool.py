from typing import Any, Dict, List, Union
import json
import sys
from tools.base_tool import BaseTool
from kernel.swarm import swarm_manager
from core.logger import logger
from tools.registry import registry

MAX_SWARM_TASKS = 50  # Previne exaustão de recursos ao spawnar agentes

class HiveDelegateTool(BaseTool):
    """
    HIVE_DELEGATE TOOL (Arkanis V3)
    Spawns an autonomous swarm of specialized agents to handle a complex project.
    Use this when a task is too big for a single agent.
    """
    
    @property
    def name(self) -> str:
        return "hive_delegate"

    @property
    def description(self) -> str:
        return "Delega um projeto complexo para um enxame de agentes especializados (The Hive)."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "project_goal": "O objetivo macro do projeto (Texto puro).",
            "sub_tasks": "Lista de dicts ou String JSON: [{'role': 'Dev', 'goal': '...'}]"
        }

    def execute(self, **kwargs) -> str:
        project_goal = kwargs.get("project_goal", "")
        raw_sub_tasks = kwargs.get("sub_tasks", [])
        
        # Validate Input Goal
        if not project_goal or not str(project_goal).strip():
            return "ERRO: O objetivo do projeto é obrigatório."
        
        cleaned_goal = str(project_goal).strip()
        tasks_list: List[Dict] = []
        
        try:
            # Handle string or list input
            if isinstance(raw_sub_tasks, str):
                tasks_list = json.loads(raw_sub_tasks)
            else:
                tasks_list = raw_sub_tasks
            
            # Schema Validation
            if not isinstance(tasks_list, list):
                raise ValueError("'sub_tasks' deve conter uma lista.")
                    
            if len(tasks_list) == 0:
                raise ValueError("'sub_tasks' não pode estar vazio.")

            # NEW: Security Check - Prevent massive spawns
            if len(tasks_list) > MAX_SWARM_TASKS:
                raise ValueError(f"Limite atingido: máximo permitido de {MAX_SWARM_TASKS} tarefas por projeto.")
                
            if not isinstance(tasks_list[0], dict):
                raise ValueError("Cada tarefa deve ser um objeto JSON (dict).")
            
            # NEW: Strict Schema Validation
            for idx, task_dict in enumerate(tasks_list):
                if not isinstance(task_dict, dict):
                    raise ValueError(f"")
                if not {'role', 'goal'}.issubset(task_dict.keys()):
                    raise ValueError(f"Tarefa {idx} está faltando as chaves 'role' ou 'goal'.")

            logger.info(f"[Hive] Desenhando enxame para: {cleaned_goal} com {len(tasks_list)} agentes.")
            swarm_manager.delegate_project(cleaned_goal, tasks_list)
            
            return f"PROJETO DELEGADO AO THE HIVE: {len(tasks_list)} agentes iniciados."
            
        except json.JSONDecodeError:
            logger.error("[Hive] Formato JSON inválido para sub_tasks", exc_info=True)
            return "FALHA NA DELEGAÇÃO: Formato JSON inválido em sub_tasks."
        except ValueError as ve:
            logger.warning(f"[Hive] Validação de entrada falhou: {ve}")
            return f"FALHA NA DELEGAÇÃO: {str(ve)}"
        except Exception as e:
            # NEW: Prevent swallowing system exit signals
            if isinstance(e, (SystemExit, KeyboardInterrupt)):
                raise
            logger.error(f"[Hive] Erro crítico ao delegar enxame: {e}", exc_info=True)
            return f"FALHA NA DELEGAÇÃO: {str(e)}"

# Auto-registry in the project ecosystem
registry.register(HiveDelegateTool())