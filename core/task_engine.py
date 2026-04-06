import threading
import time
import uuid
from typing import Dict, Any, List
from datetime import datetime
from kernel.agent import ArkanisAgent
import logging

logger = logging.getLogger(__name__)

class ContinuousTask:
    def __init__(self, description: str, type_: str, interval: int, condition: str = "", goal_id: str = None, auto_generated: bool = False):
        if interval < 1:
            raise ValueError(\"Interval must be at least 1 second\")
        if type_ not in [\"interval\", \"condition\"]:
            raise ValueError(\"Type must be 'interval' or 'condition'\")
            
        self.id = str(uuid.uuid4())[:8]
        self.description = description
        self.type = type_
        self.interval = interval
        self.condition = condition
        self.goal_id = goal_id
        self.auto_generated = auto_generated
        self.status = \"running\"
        self.created_at = datetime.now()
        self.last_run = None
        self.next_run = None
        self.agent = ArkanisAgent(agent_id=self.id)
        self.thread = None
        self.run_count = 0
        self.last_result = ""

    def to_dict(self):
        return {
            \"id\": self.id,
            \"description\": self.description,
            \"type\": self.type,
            \"interval\": self.interval,
            \"condition\": self.condition,
            \"goal_id\": self.goal_id,
            \"auto_generated\": self.auto_generated,
            \"status\": self.status,
            \"created_at\": self.created_at.strftime(\"%Y-%m-%d %H:%M:%S\"),
            \"last_run\": self.last_run.strftime(\"%Y-%m-%d %H:%M:%S\") if self.last_run else None,
            \"next_run\": self.next_run.strftime(\"%Y-%m-%d %H:%M:%S\") if self.next_run else None,
            \"run_count\": self.run_count,
            \"last_result\": self.last_result,
            \"agent_status\": self.agent.status,
            \"recent_logs\": [log for log in self.agent.logs[-5:]] if hasattr(self.agent, \"logs\") else []
        }


class TaskEngine:
    def __init__(self):
        self.tasks: Dict[str, ContinuousTask] = {}
        self._tasks_lock = threading.Lock()
        self._shutdown_event = threading.Event()
        self.engine_thread = threading.Thread(target=self._engine_loop, name=\"TaskEngine-Loop\", daemon=True)
        self.engine_thread.start()
        logger.info(\"Task engine started\")

    def start_task(self, description: str, type_: str, interval: int, condition: str = \"\", goal_id: str = None, auto_generated: bool = False) -> ContinuousTask:
        with self._tasks_lock:
            task = ContinuousTask(description, type_, interval, condition, goal_id, auto_generated)
            from core.goal_manager import goal_manager
            if goal_id:
                try:
                    goal_manager.assign_agent(goal_id, task.id)
                except Exception as e:
                    logger.error(f\"Failed to assign agent to goal {goal_id}: {e}\")
            self.tasks[task.id] = task
            task.next_run = datetime.now()
            logger.info(f\"Task {task.id} started with interval {interval}s\")
            return task

    def stop_task(self, task_id: str) -> bool:
        with self._tasks_lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = \"stopped\"
                try:
                    task.agent.stop_requested.set()
                except AttributeError:
                    pass
                # Optionally clean up stopped tasks after a timeout
                return True
        return False

    def start_engine(self):
        \"\"\"Restart the engine loop after shutdown\"\"\"
        self._shutdown_event.clear()
        self.engine_thread = threading.Thread(target=self._engine_loop, name=\"TaskEngine-Loop\", daemon=True)
        self.engine_thread.start()
        logger.info(\"Task engine restarted\")

    def shutdown(self):
        \"\"\"Graceful shutdown of the engine and all tasks\"\"\"
        self._shutdown_event.set()
        with self._tasks_lock:
            # Stop all running tasks
            for task in self.tasks.values():
                task.status = \"stopped\"
                try:
                    task.agent.stop_requested.set()
                except AttributeError:
                    pass
        self.engine_thread.join(timeout=5)
        logger.info(\"Task engine shut down\")

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self._tasks_lock:
            return [t.to_dict() for t in self.tasks.values()]

    def _engine_loop(self):
        while not self._shutdown_event.is_set():
            now = datetime.now()
            with self._tasks_lock:
                active_tasks = list(self.tasks.values())
            
            for task in active_tasks:
                if task.status == \"stopped\":
                    continue
                
                if task.next_run and now >= task.next_run:
                    # Prevent overlapping executions
                    if task.agent.status not in [\"idle\", \"completed\", \"failed\"]:
                        continue
                        
                    task.last_run = now
                    threading.Thread(
                        target=self._execute_task_tick,
                        args=(task,),
                        name=\"Task-\" + task.id,
                        daemon=True
                    ).start()
                    
                    task.next_run = datetime.fromtimestamp(now.timestamp() + task.interval)
            
            self._shutdown_event.wait(timeout=1)

    def _execute_task_tick(self, task: ContinuousTask):
        task.run_count += 1
        prompt = task.description
        if task.type == \"condition\" and task.condition:
            prompt = f\"Avalie a condição: {task.condition}. Depois execute: {task.description}\"
            
        task.agent.mode = \"auto\"
        task.agent.status = \"idle\"
        task.agent.stop_requested.clear()
        task.agent.auto_results = []
        
        try:
            res = task.agent._handle_auto_mode(prompt)
            task.last_result = res
        except Exception as e:
            error_msg = f\"Error executing task {task.id}: {e}\"
            task.last_result = error_msg
            logger.error(error_msg)
            try:
                task.agent.log(str(e), \"error\")
            except AttributeError:
                pass


task_engine = TaskEngine()

