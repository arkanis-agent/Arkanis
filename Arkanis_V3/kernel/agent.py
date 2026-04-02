from kernel.planner import Planner
from kernel.executor import Executor
from core.agents.critic_agent import CriticAgent
from modules.memory.short_term import session_memory
from rich import print as rprint
from rich.panel import Panel
from core.agent_bus import agent_bus
from core.goal_manager import goal_manager
from modules.memory.long_term import long_term_memory
import time
import threading
import uuid
from core.logger import logger as arkanis_logger
from core.llm_client import LLMClient

class ArkanisAgent:
    """
    Main Agent class for ARKANIS V3.
    Coordinates between Thinking (Planner) and Acting (Executor).
    """
    def __init__(self, agent_id: str = None):
        self.id = agent_id if agent_id else "main"
        self.planner = Planner()
        self.executor = Executor()
        self.critic = CriticAgent()
        self.memory = session_memory
        
        # Agent Control State
        self.mode = "manual"
        self.status = "idle"
        self.current_cycle = 0
        self.goal = None
        self.auto_results = []
        self.logs = [] # Log buffer for WebUI
        
        # Threading/Control Events
        self.stop_requested = threading.Event()
        self.pause_requested = threading.Event()
        self.resume_requested = threading.Event()
        self.auto_thread = None
        
        # Communication
        self.inbox = []
        agent_bus.register_agent(self.id, self)
        
    def __del__(self):
        try:
            agent_bus.unregister_agent(self.id)
        except:
            pass

    def log(self, message: str, log_type: str = "info"):
        """Centralized logging for both CLI (rich), WebUI (buffer), and System Logs."""
        clean_msg = str(message).strip()
        timestamp = time.strftime("%H:%M:%S")
        
        # WebUI Buffer (limit to 100 most recent logs)
        self.logs.append({"time": timestamp, "type": log_type, "message": clean_msg})
        if len(self.logs) > 100:
            self.logs.pop(0)

        # Delegate to the Arkanis Production Logger
        if log_type == "error":
            arkanis_logger.error(clean_msg)
        elif log_type == "success":
            arkanis_logger.success(clean_msg)
        elif log_type == "warning" or log_type == "control":
            arkanis_logger.warning(clean_msg)
        elif log_type == "critic":
            arkanis_logger.critic(clean_msg)
        else:
            # Default to info with a custom symbol if possible
            symbols = {"planner": "🧠", "executor": "⚙️", "system": "💻"}
            symbol = symbols.get(log_type, "🧠")
            arkanis_logger.info(clean_msg, symbol=symbol)

    def handle_input(self, user_input: str) -> str:
        """Process user input with strict priority routing."""
        # Clean and lower for processing
        clean_input = user_input.strip()
        lower_input = clean_input.lower()
        
        # 1. CONTROL LAYER (pause, resume, stop, status)
        if lower_input == "status":
            return self._get_status_report()
            
        if lower_input == "pause":
            self.status = "paused"
            self.pause_requested.set()
            self.log("Agent paused between cycles.", "control")
            return "[Control] Agent paused between cycles."
            
        if lower_input == "resume":
            if self.status == "paused":
                self.status = "running"
                self.pause_requested.clear()
                self.resume_requested.set()
                self.log("Agent resuming...", "control")
                return "[Control] Agent resuming..."
            return "[Control] Agent is not paused."
            
        if lower_input == "stop":
            self.status = "idle"
            self.stop_requested.set()
            self.pause_requested.clear()
            self.resume_requested.set() 
            self.log("Stop signal sent. Resetting to IDLE.", "control")
            return "[Control] Stop signal sent. Resetting to IDLE."

        # 2. AUTO MODE (prefix based)
        if lower_input.startswith("auto:") or lower_input.startswith("objetivo:"):
            if self.status != "idle":
                return f"[Warning] Agent is currently {self.status}. Stop or finish current task first."
            
            # Extract target goal
            self.goal = clean_input.split(":", 1)[1].strip()
            self.mode = "auto"
            
            # Launch async thread
            self.auto_thread = threading.Thread(target=self._handle_auto_mode, args=(self.goal,), daemon=True)
            self.auto_thread.start()
            
            return f"[Control] Auto Mode started for objective: '{self.goal}'. Type 'status' for progress."

        # 3. MANUAL MODE (standard planning)
        self.mode = "manual"
        return self._handle_manual_mode(clean_input)

    def _get_status_report(self) -> str:
        """Detailed Agent Status Panel."""
        report = f"Mode: {self.mode.upper()} | Status: {self.status.upper()} | Cycle: {self.current_cycle}/5"
        self.log(report, "system")
        return f"Status checked: {self.status.upper()}"

    def _format_response_with_soul(self, user_input: str, raw_results: list) -> str:
        """Format tool results into a natural, SOUL-aligned response in Portuguese."""
        from core.llm_client import LLMClient
        soul = self.planner.agent_identity
        raw = "\n".join(raw_results)

        system_prompt = f"""Você é ARKANIS. Sua personalidade e valores:
{soul}

REGRAS DE RESPOSTA:
- Responda sempre em Português do Brasil.
- Seja natural, direto e amigável — nunca robótico ou formal demais.
- Nunca exiba JSON cru — interprete e apresente dados de forma conversacional.
- GROUNDING CRÍTICO: Nunca invente links, notícias ou fatos que não foram explicitamente retornados pelas ferramentas.
- GROUNDING CRÍTICO: Se uma ferramenta falhar (timeout, erro 404, etc), relate a impossibilidade de forma simples: "Não consegui acessar a página X" em vez de inventar detalhes do erro.
- PROIBIÇÃO: Nunca use placeholders como [key point], [Summarized point] ou similares. Se não houver informação, não diga nada.
- Mantenha respostas concisas mas completas."""

        user_prompt = f"""O usuário disse: "{user_input}"

Dados obtidos pelas ferramentas:
{raw}

Formule uma resposta natural e amigável."""

        llm = LLMClient()
        response = llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        if response and "[Error" not in response:
            return response
        return raw  # fallback to raw if formatter fails

    def _handle_manual_mode(self, user_input: str) -> str:
        """Process user input manually: Context -> Plan -> Execute -> Remember."""
        # 1. Recuperar contexto da Memória e extrair Inbox
        context = self.memory.get_context()

        # Injetar Memória de Longo Prazo
        lt_mem = long_term_memory.get_formatted_memory()
        if lt_mem:
            context += f"\n\n[MEMÓRIA DE LONGO PRAZO / HIVE]:\n{lt_mem}"

        if self.inbox:
            messages = "\n".join([f"De {m['from']}: {m['content']}" for m in self.inbox])
            context += f"\n\n[MENSAGENS NÃO LIDAS DOS AGENTES]:\n{messages}"
            self.inbox.clear()

        # Injetar Objetivos Globais Ativos
        active_goals = [g for g in goal_manager.goals.values() if g.status == "active"]
        if active_goals:
            goals_str = "\n".join([f"- Goal [{g.id}]: {g.description} | Progresso: {g.progress}%" for g in active_goals])
            context += f"\n\n[OBJETIVOS GLOBAIS DO SISTEMA (GOAL MANAGER)]:\n{goals_str}"

        # 2. Planning with Critic Gate
        max_refinements = 2
        refine_count = 0
        final_plan = None
        
        while refine_count <= max_refinements:
            self.log(f"Iniciando planejamento (Tentativa {refine_count + 1}) para: '{user_input}'", "planner")
            plan = self.planner.plan(user_input, recent_context=context)
            
            for i, step in enumerate(plan, 1):
                tool = step.get('tool', 'unknown')
                self.log(f"Passo {i}: {tool}", "planner")

            # CRITIC GATE (Pre-Execution)
            self.log("Critic analisando plano antes da execução...", "critic")
            critic_report = self.critic.evaluate_plan(goal=user_input, plan=plan, context=context, soul=self.planner.agent_identity)
            
            decision = critic_report.get("decision", "improve")
            score = critic_report.get("quality_score", 0)
            reasoning = critic_report.get("reasoning", "")

            self.log(f"Auditoria: {decision.upper()} | Score: {score}/10", "critic")
            if reasoning:
                self.log(f"Raciocínio: {reasoning}", "critic")

            if decision == "approve":
                self.log("Plano APROVADO pelo Auditor Sênior.", "success")
                final_plan = plan
                break
            elif decision == "improve" and refine_count < max_refinements:
                self.log(f"🔄 Auditor sugeriu melhorias (Refinamento {refine_count + 1}/2).", "critic")
                for issue in critic_report.get("issues", []):
                    self.log(f"⚠️ {issue}", "critic")
                # Feedback loop: add critic suggestion to context for next planning attempt
                context += f"\n\n[FEEDBACK DO AUDITOR]: {critic_report.get('improved_plan')}"
                refine_count += 1
                continue
            else:
                self.log(f"🔴 Auditor REJEITOU o plano: {critic_report.get('final_suggestion')}", "error")
                return f"Execução abortada por segurança: {critic_report.get('final_suggestion')}"

        # 3. Execution (Fixed Plan)
        self.log("Executando plano validado...", "executor")
        results = self.executor.execute_plan(final_plan)
        
        # LEARNING LOOP: Feedback results to Critic
        self.critic.record_execution_result(user_input, results)

        for res in results:
            self.log(f"Resultado: {res[:100]}...", "executor")

        # 4. Format response with SOUL personality
        self.log("Formatando resposta com SOUL...", "system")
        response = self._format_response_with_soul(user_input, results)

        # 5. Salvar Interação Histórica Completa na Memória
        self.memory.add_interaction(user_input=user_input, plan=final_plan, result=response)

        return response

    def _handle_auto_mode(self, goal: str) -> str:
        """Process a complex goal autonomously with up to 5 iterative cycles."""
        self.status = "running"
        self.stop_requested.clear()
        self.pause_requested.clear()
        self.resume_requested.clear()
        
        self.log(f"Iniciado Auto Mode. Objetivo: {goal}", "system")
        
        max_cycles = 5
        self.current_cycle = 1
        self.auto_results = []
        
        while self.current_cycle <= max_cycles:
            # Check for STOP
            if self.stop_requested.is_set():
                self.log("Execução cancelada pelo usuário.", "control")
                self.status = "idle"
                break
                
            # Check for PAUSE
            if self.pause_requested.is_set():
                self.log("Pausado. Aguardando comando 'resume'...", "control")
                self.status = "paused"
                self.resume_requested.wait() # Block until resume is set
                if self.stop_requested.is_set(): continue # Re-check stop after resume
                self.log("Retomando execução.", "control")
                self.status = "running"
                self.pause_requested.clear()
                self.resume_requested.clear()

            self.log(f"Iniciando Ciclo {self.current_cycle}/{max_cycles}", "system")
            
            context = self.memory.get_context()
            
            # Injetar Memória de Longo Prazo
            lt_mem = long_term_memory.get_formatted_memory()
            if lt_mem:
                context += f"\n\n[MEMÓRIA DE LONGO PRAZO / HIVE]:\n{lt_mem}"
                
            if self.inbox:
                messages = "\n".join([f"De {m['from']}: {m['content']}" for m in self.inbox])
                context += f"\n\n[MENSAGENS NÃO LIDAS DOS AGENTES]:\n{messages}"
                self.inbox.clear()
                self.log("Lendo mensagens do Agent Bus...", "system")
                
            # Injetar Objetivos Globais Ativos
            active_goals = [g for g in goal_manager.goals.values() if g.status == "active"]
            if active_goals:
                goals_str = "\n".join([f"- Goal [{g.id}]: {g.description} | Progresso: {g.progress}%" for g in active_goals])
                context += f"\n\n[OBJETIVOS GLOBAIS DO SISTEMA (GOAL MANAGER)]:\n{goals_str}"
                
            # --- PLANNING & CRITIC GATE ---
            max_refinements = 2
            refine_count = 0
            final_plan = None
            
            auto_prompt = (
                f"OBJETIVO GLOBAL A SER ATINGIDO: {goal}\n\n"
                f"Verifique o CONTEXTO RECENTE. Se o objetivo já foi 100% atingido pelos resultados anteriores, "
                f"você DEVE retornar APENAS a ferramenta 'print_message' indicando conclusão exata.\n"
                f"Se ainda faltam ações, retorne os próximos passos lógicos."
            )

            while refine_count <= max_refinements:
                self.log(f"Replanejando passos (Tentativa {refine_count + 1})...", "planner")
                plan = self.planner.plan(auto_prompt, recent_context=context)
                
                # CRITIC GATE (Pre-Execution Audit)
                critic_report = self.critic.evaluate_plan(goal=goal, plan=plan, context=context, soul=self.planner.agent_identity)
                
                decision = critic_report.get("decision", "improve")
                score = critic_report.get("quality_score", 0)
                reasoning = critic_report.get("reasoning", "")
                
                self.log(f"Auditoria Ciclo: {decision.upper()} | Score: {score}/10", "critic")
                if reasoning:
                    self.log(f"Raciocínio: {reasoning}", "critic")

                if decision == "approve":
                    self.log("Ciclo aprovado para execução.", "success")
                    final_plan = plan
                    break
                elif decision == "improve" and refine_count < max_refinements:
                    self.log(f"🔄 Auditor solicitou melhorias (Refinamento {refine_count + 1}/2).", "critic")
                    context += f"\n\n[AUDITOR FEEDBACK]: {critic_report.get('improved_plan')}"
                    refine_count += 1
                else:
                    self.log(f"⚠️ Auditor REJEITOU o ciclo: {critic_report.get('final_suggestion')}", "error")
                    self.status = "failed"
                    return f"Ciclo interrompido por segurança: {critic_report.get('final_suggestion')}"

            # --- EXECUTION ---
            self.log("Processando execução do ciclo validado...", "executor")
            results = self.executor.execute_plan(final_plan)
            
            # LEARNING LOOP: Feedback results to Critic
            self.critic.record_execution_result(goal, results)
            
            combined_result = "\n".join(results)
            self.auto_results.extend(results)
            
            for res in results:
                self.log(f"Log: {res[:100]}...", "executor")
            
            self.memory.add_interaction(user_input=f"Ciclo Auto {self.current_cycle} - {goal}", plan=final_plan, result=combined_result)
            
            # Final check for objective completion vs progress
            if "objetivo atingido" in combined_result.lower() or "finalizado" in combined_result.lower():
                self.log("Objetivo atingido com sucesso.", "success")
                self.status = "completed"
                break
            
            elif decision == "reject":
                self.log("⚠️ Auditor Sênior Rejeitou a Saída (Risco ou Erro). Abortando.", "error")
                self.auto_results.append(f"Aviso: Auditor rejeitou a ação: {critic_report.get('final_suggestion')}")
                self.status = "failed"
                break
                
            elif decision == "improve":
                self.log("🔄 Auditor solicitou melhorias. Replanejando...", "critic")
                # We inject the improved plan or logic into the next cycle's context
                if critic_report.get("improved_plan"):
                    self.memory.add_interaction(user_input="CRITIC IMPROVEMENT PLAN", plan=[], result=f"Sugestão do Auditor: {critic_report['improved_plan']}")
                
            self.current_cycle += 1
            if self.current_cycle <= max_cycles:
                time.sleep(1) # Visual pacing
                
        if self.current_cycle > max_cycles and self.status == "running":
            self.log("Limite de ciclos atingido (5). Abortando loop.", "error")
            self.auto_results.append("Aviso: Modo automático interrompido por limite de segurança (5 ciclos).")
            self.status = "failed"
            
        final_response = "\n".join(self.auto_results)
        self.log("Sistema de Objetivo Finalizado.", "system")
        
        # Reset state back to idle if not paused/failed/completed in a specific way
        if self.status != "paused":
            self.mode = "manual"
            if self.status == "running": self.status = "idle"
            
        self.log(f"Tarefa Finalizada para: '{goal}'", "system")
        return final_response
