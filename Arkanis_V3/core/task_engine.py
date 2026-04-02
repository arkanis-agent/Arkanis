import threading
import time
import uuid
from typing import Dict, Any, List
from datetime import datetime
from kernel.agent import ArkanisAgent

class ContinuousTask:
    def __init__(self, description: str, type_: str, interval: int, condition: str = "", goal_id: str = None, auto_generated: bool = False):
        self.id = str(uuid.uuid4())[:8]
        self.description = description
        self.type = type_ # "interval" or "condition"
        self.interval = interval # in seconds
        self.condition = condition
        self.goal_id = goal_id
        self.auto_generated = auto_generated
        self.status = "running" # running, paused, stopped
        self.created_at = datetime.now()
        self.last_run = None
        self.next_run = None
        self.agent = ArkanisAgent(agent_id=self.id) # Independent agent for this task
        self.thread = None
        self.run_count = 0
        self.last_result = ""

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type,
            "interval": self.interval,
            "condition": self.condition,
            "goal_id": self.goal_id,
            "auto_generated": self.auto_generated,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "last_run": self.last_run.strftime("%Y-%m-%d %H:%M:%S") if self.last_run else None,
            "next_run": self.next_run.strftime("%Y-%m-%d %H:%M:%S") if self.next_run else None,
            "run_count": self.run_count,
            "last_result": self.last_result,
            "agent_status": self.agent.status,
            "recent_logs": [log for log in self.agent.logs[-5:]] # Send last 5 logs for real-time tracking
        }

class TaskEngine:
    def __init__(self):
        self.tasks: Dict[str, ContinuousTask] = {}
        self.running = True
        self.engine_thread = threading.Thread(target=self._engine_loop, daemon=True)
        self.engine_thread.start()

    def start_task(self, description: str, type_: str, interval: int, condition: str = "", goal_id: str = None, auto_generated: bool = False) -> ContinuousTask:
        task = ContinuousTask(description, type_, interval, condition, goal_id, auto_generated)
        # Agent ID is now assigned during ContinuousTask.__init__
        from core.goal_manager import goal_manager
        if goal_id:
            goal_manager.assign_agent(goal_id, task.id)
            
        self.tasks[task.id] = task
        task.next_run = datetime.now()
        return task

    def stop_task(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "stopped"
            # Attempt to stop the agent if it's currently running
            task.agent.stop_requested.set()
            return True
        return False

    def list_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.tasks.values()]

    def _engine_loop(self):
        while self.running:
            now = datetime.now()
            for task in list(self.tasks.values()):
                if task.status == "stopped":
                    continue
                
                # Check if it's time to run
                if task.next_run and now >= task.next_run:
                    # If the agent is currently busy doing a previous cycle, skip this tick
                    if task.agent.status != "idle" and task.agent.status != "completed" and task.agent.status != "failed":
                        continue
                        
                    task.last_run = now
                    # Launch execution thread for this tick
                    threading.Thread(target=self._execute_task_tick, args=(task,), daemon=True).start()
                    
                    # Schedule next run
                    task.next_run = datetime.fromtimestamp(now.timestamp() + task.interval)
            
            time.sleep(1)

    def _execute_task_tick(self, task: ContinuousTask):
        task.run_count += 1
        prompt = task.description
        if task.type == "condition" and task.condition:
            prompt = f"Avalie a condição: {task.condition}. Depois execute: {task.description}"
            
        # We manually call _handle_auto_mode blocks in this tick thread
        # This gives us full auto-cycle (planner+tools+critic) independently
        task.agent.mode = "auto"
        # Reset agent state for the new cycle
        task.agent.status = "idle"
        task.agent.stop_requested.clear()
        task.agent.auto_results = []
        
        try:
            res = task.agent._handle_auto_mode(prompt)
            task.last_result = res
        except Exception as e:
            task.last_result = f"Error: {str(e)}"
            task.agent.log(f"Error executing task: {e}", "error")

task_engine = TaskEngine()
