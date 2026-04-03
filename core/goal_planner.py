import time
import threading
import json
from datetime import datetime
from core.goal_manager import goal_manager
from core.task_engine import task_engine
from core.llm_router import router
from core.agent_bus import agent_bus
from core.cost_governor import governor

class GoalPlanner:
    def __init__(self):
        self.running = True
        self.interval = 60 # Check every 60 seconds
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            self._evaluate_goals()
            time.sleep(self.interval)

    def _evaluate_goals(self):
        for goal in list(goal_manager.goals.values()):
            if goal.status != "active":
                continue

            # Check currently running tasks for this goal
            active_tasks = [t for t in task_engine.tasks.values() if t.goal_id == goal.id and t.status == "running"]
            active_descriptions = [t.description.lower() for t in active_tasks]

            # If we already have 3+ tasks running for this goal, let's wait to not overload
            if len(active_tasks) >= 3:
                continue

            self._plan_tasks_for_goal(goal, active_descriptions)

    def _plan_tasks_for_goal(self, goal, active_descriptions):
        prompt = (
            f"O sistema possui um OBJETIVO GLOBAL ATIVO:\n"
            f"ID: {goal.id}\n"
            f"Descrição: {goal.description}\n"
            f"Progresso atual: {goal.progress}%\n\n"
            f"As seguintes tarefas já estão rodando para este objetivo: {active_descriptions}\n\n"
            f"Crie até 2 novas tarefas contínuas necessárias para avançar este objetivo. "
            f"Exemplos de perfis: 'monitor_agent' para coleta, 'research_agent' para análise, 'dev_agent' para gerar/editar código. "
            f"IMPORTANTE PARA DEV_AGENT: Se o objetivo envolve modificar ou criar código, exija o uso das ferramentas write_file, read_file e list_files na descrição. Aja de forma autônoma para evoluir o próprio sistema ou qualquer código se for um objetivo, e grave Logs no Agent Bus. "
            f"Responda APENAS com um array JSON válido onde cada objeto possui:\n"
            f"- 'description': a instrução clara para a tarefa (incluindo o perfil assumido). Se quiser um dev_agent, inicie a descrição com 'Você é o dev_agent...'\n"
            f"- 'type': 'interval'\n"
            f"- 'interval': número de segundos (ex 300)\n"
            f"Não use markdown, retorne a string JSON bruta [{{...}}]. Se nenhuma nova tarefa for necessária, retorne []."
        )

        try:
            response = router.generate(prompt)
            clean_res = response.strip()
            if clean_res.startswith("```json"):
                clean_res = clean_res[7:]
            if clean_res.endswith("```"):
                clean_res = clean_res[:-3]
            
            new_tasks_data = json.loads(clean_res)
            
            for task_data in new_tasks_data:
                desc = task_data.get("description", "")
                if desc.lower() not in active_descriptions:
                    # Checagem de Governador de Custos e Recursos
                    active_now = sum(1 for t in task_engine.tasks.values() if t.status == "running")
                    goal_now = len(active_descriptions)
                    
                    if not governor.can_start_task(goal.id, active_now, goal_now):
                        print(f"[GoalPlanner] Blocked spawn of task '{desc}' due to Governor Limits.")
                        agent_bus.broadcast_message("GoalPlanner", f"Governor Blocked auto-task '{desc}' for goal {goal.id}")
                        continue
                        
                    # Spawna a nova task via task engine as auto_generated
                    task_engine.start_task(
                        description=desc,
                        type_=task_data.get("type", "interval"),
                        interval=task_data.get("interval", 300),
                        goal_id=goal.id,
                        auto_generated=True
                    )
                    # Notificar via agent bus
                    agent_bus.broadcast_message("GoalPlanner", f"Spawned auto-task '{desc}' for goal {goal.id}")
                    # Update local ref to avoid immediate dup in same loop
                    active_descriptions.append(desc.lower())

        except Exception as e:
            print(f"[GoalPlanner] Error auto-generating tasks for goal {goal.id}: {e}")

goal_planner = GoalPlanner()
