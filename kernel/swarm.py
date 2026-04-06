from typing import List, Dict, Any, Optional
import threading
import uuid
import time
from core.agent_bus import agent_bus
from core.llm_client import LLMClient
from core.logger import logger


class SwarmWorker:
    """A temporary specialized agent spawned by the Hive."""
    _DEFAULT_TIMEOUT = 300  # 5 minutos padrão
    _MAX_LOGS = 5  # Limitar logs para evitar memória

    def __init__(self, role: str, goal: str, parent_id: str = "main", timeout: int = None):
        self.id = f"worker_{role.lower().replace(' ', '_')}_{str(uuid.uuid4())}"
        self.role = role
        self.goal = goal
        self.parent_id = parent_id
        self.status = "idle"
        self.mode = "AUTO"
        self.current_action = "Inicializando..."
        self.is_custom = True
        self.logs = []
        self.timeout = timeout or self._DEFAULT_TIMEOUT
        self._event = threading.Event()
        self._result = None
        self._exception = None
        self._lock = threading.Lock()

        # Register in bus (thread-safe)
        try:
            agent_bus.register_agent(self.id, self)
            logger.info(f"[Hive] Novo worker spawned: {self.id} ({self.role})")
        except Exception as e:
            logger.error(f"[Hive] Falha ao registrar worker: {e}")

    def run(self):
        """Execute the worker's dedicated task with error handling."""
        self.status = "running"
        self.current_action = f"Trabalhando em: {self.goal[:30]}..."

        try:
            system_prompt = f"Você é o agente especialista {self.role}. Seu objetivo único é: {self.goal}. Responda de forma técnica e direta."
            user_prompt = f"Execute sua tarefa agora no contexto de Arkanis V3."

            llm = LLMClient()
            self._result = llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )

            self._log_event("success", "Tarefa concluída.")
            self.status = "idle"
            self.current_action = "Concluído. Aguardando recall."

        except Exception as e:
            self._exception = str(e)
            self._log_event("error", f"Falha na execução: {e}")
            self.status = "idle"
            self.current_action = f"Falhou: {str(e)[:30]}"
            self._result = None
            logger.error(f"[Worker {self.id}] Exceção: {e}")
        finally:
            # Notify parent via bus
            try:
                if self._result:
                    agent_bus.send_message(self.id, self.parent_id, f"WORKER_DONE:{self.id}: {str(self._result)[:200]}")
                else:
                    agent_bus.send_message(self.id, self.parent_id, f"WORKER_FAILED:{self.id}: {self._exception or "Desconhecido"}")
            except Exception as e:
                logger.error(f"[Worker {self.id}] Falha ao notificar bus: {e}")

            # Release for cleanup
            self._event.set()
            agent_bus.unregister_agent(self.id)

    def _log_event(self, type: str, message: str):
        """Thread-safe logging with limit."""
        with self._lock:
            entry = {"time": time.strftime("%H:%M:%S"), "type": type, "message": message}
            self.logs.append(entry)
            if len(self.logs) > self._MAX_LOGS:
                self.logs.pop(0)

    def wait(self, timeout: float = None) -> Optional[str]:
        """Wait for worker to complete and return result."""
        self._event.wait(timeout=timeout or self.timeout)
        return self._result

    def get_exception(self) -> Optional[str]:
        """Retrieve exception if worker failed."""
        return self._exception


class SwarmManager:
    """Orchestrator for the Hive Swarm."""

    def __init__(self):
        self.active_workers: List[SwarmWorker] = []
        self._lock = threading.Lock()
        self._maintenance_thread = None
        self._should_stop = False

    def start(self):
        """Start maintenance daemon thread."""
        self._should_stop = False
        self._maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._maintenance_thread.start()

    def stop(self):
        """Stop maintenance daemon thread."""
        self._should_stop = True
        if self._maintenance_thread:
            self._maintenance_thread.join(timeout=5)

    def _maintenance_loop(self):
        """Periodically clean up idle workers."""
        while not self._should_stop:
            self.cleanup()
            time.sleep(60)  # Cleanup a cada 60 segundos

    def delegate_project(self, project_goal: str, sub_tasks: List[Dict[str, str]]):
        """Spawns workers for each sub-task."""
        logger.info(f"[Hive] Delegando projeto complexo para {len(sub_tasks)} workers.")

        for task in sub_tasks:
            worker = SwarmWorker(role=task['role'], goal=task['goal'])
            with self._lock:
                self.active_workers.append(worker)
            threading.Thread(target=worker.run, daemon=True).start()

    def cleanup(self):
        """Removes finished workers from the bus."""
        with self._lock:
            idle_workers = [w for w in self.active_workers if w.status == "idle"]

        for worker in idle_workers:
            agent_bus.unregister_agent(worker.id)
            logger.info(f"[Hive] Limpando worker finalizado: {worker.id}")

        with self._lock:
            self.active_workers = [w for w in self.active_workers if w.status == "running"]

    def get_stats(self) -> Dict[str, int]:
        """Return worker statistics."""
        with self._lock:
            running = sum(1 for w in self.active_workers if w.status == "running")
            idle = sum(1 for w in self.active_workers if w.status == "idle")
            failed = sum(1 for w in self.active_workers if "error" in [log.get("type") for log in w.logs])
            return {
                "total": len(self.active_workers),
                "running": running,
                "idle": idle,
                "failed": failed
            }


swarm_manager = SwarmManager()
swarm_manager.start()  # Iniciar maintenance thread automaticamente