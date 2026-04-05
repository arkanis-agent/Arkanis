from typing import List, Optional, Dict
from kernel.planner import Planner
from kernel.executor import Executor
from core.agents.critic_agent import CriticAgent
from core.agents.auto_heal_agent import AutoHealAgent # New: Auto-Heal System
from core.agents.dev_agent import DevAgent # New: Dev Center
from core.agents.architect_agent import ArchitectAgent # New: Maestro Architect
from core.agents.scheduler_agent import SchedulerAgent # New: Background Reminder Agent
from modules.memory.short_term import session_memory
from rich import print as rprint
from rich.panel import Panel
from core.agent_bus import agent_bus
from core.goal_manager import goal_manager
from modules.memory.long_term import long_term_memory
from modules.memory.vector import chronos_memory # New: Neural Hive Context
import time
import threading
import uuid
from core.logger import logger as arkanis_logger
from core.llm_client import LLMClient
from core.model_strategy import strategy_engine
from core.decision_auditor import decision_auditor # NEW: Decision Auditor
from tools import registry
import os

class ArkanisAgent:
    """
    Main Agent class for ARKANIS V3.
    Coordinates between Thinking (Planner) and Acting (Executor).
    """
    def __init__(self, 
                 agent_id: str = None, 
                 planner: Optional[Planner] = None, 
                 executor: Optional[Executor] = None, 
                 critic: Optional[CriticAgent] = None):
        self.id = agent_id if agent_id else "main"
        
        # Dependency Injection: Use provided components or default to new ones
        self.planner = planner if planner else Planner()
        self.executor = executor if executor else Executor()
        self.critic = critic if critic else CriticAgent()
        
        # Fixed system components
        self.sentinel = AutoHealAgent() # The Self-Maintenance Sentinel
        self.dev_agent = DevAgent() # The Developer Agent
        self.architect = ArchitectAgent() # The Master Architect (Maestro)
        self.scheduler = SchedulerAgent(self) # The Agenda & Reminder Manager
        
        # Start background autonomous loops
        self.sentinel.start_loop()
        self.dev_agent.start_loop()
        self.architect.start_loop()
        self.scheduler.start_loop()
        
        self.memory = session_memory
        
        # Agent Control State
        self.mode = "manual"
        self.status = "idle"
        self.current_cycle = 0
        self.goal = None
        self.auto_results = []
        self.logs = [] # Log buffer for WebUI
        self.last_panic_time = 0 # Cooldown limit for Sentinel reflex
        
        # Agent Identity & Capabilities (for Control Center)
        self.role = "Agente Principal"
        self.current_action = "Idle"
        self.allowed_tools = []  # Empty = all tools allowed
        self.is_custom = False   # True for user-created agents
        
        # Threading/Control Events
        self.stop_requested = threading.Event()
        self.pause_requested = threading.Event()
        self.resume_requested = threading.Event()
        self.auto_thread = None
        
        # Communication
        self.inbox = []
        # 2. Register with Bus
        agent_bus.register_agent(self.id, self)
        agent_bus.register_agent(self.sentinel.id, self.sentinel)
        agent_bus.register_agent(self.dev_agent.id, self.dev_agent)
        agent_bus.register_agent(self.architect.id, self.architect)
        
        # Virtual Sub-Agents for UI / Multi-Agent Simulation
        from collections import namedtuple
        VirtualAgent = namedtuple('VirtualAgent', ['id', 'status', 'mode', 'current_cycle'])
        agent_bus.register_agent("planner_agent", VirtualAgent("planner_agent", "idle", "AUTO", 0))
        agent_bus.register_agent("memory_agent", VirtualAgent("memory_agent", "idle", "AUTO", 0))
        agent_bus.register_agent("goal_agent", VirtualAgent("goal_agent", "idle", "AUTO", 0))
        agent_bus.register_agent("tool_agent", VirtualAgent("tool_agent", "idle", "AUTO", 0))
        
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

    def handle_input(self, user_input: str, images: Optional[List[str]] = None, files: Optional[List[Dict[str, str]]] = None) -> str:
        """Process user input with strict priority routing and vision support."""
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

        # 2. AUTO MODE / GOAL MODE (prefix based)
        if lower_input.startswith("auto:") or lower_input.startswith("objetivo:"):
            if self.status != "idle":
                return f"[Warning] O agente já está ocupado ({self.status}). Pare ou aguarde antes de iniciar um novo objetivo global."
            
            # Extract target goal
            g_desc = clean_input.split(":", 1)[1].strip()
            self.goal = g_desc
            self.mode = "auto"
            
            # Create in GoalManager for persistence
            new_goal = goal_manager.create_goal(g_desc, priority="high")
            self.log(f"Objetivo Global criado [ID: {new_goal.id}]: {g_desc}", "success")
            
            # Launch async thread
            self.auto_thread = threading.Thread(target=self._handle_auto_mode, args=(self.goal,), daemon=True)
            self.auto_thread.start()
            
            return f"🚀 [SENTINEL] Modo Auto iniciado: '{self.goal}'. O sistema irá persistir até concluir (ID: {new_goal.id})."

        # 3. GOAL MANAGEMENT COMMANDS
        if lower_input.startswith("concluir "):
            g_id = lower_input.replace("concluir ", "").strip()
            goal_manager.update_status(g_id, "completed")
            return f"✅ Objetivo {g_id} marcado como concluído."
            
        if lower_input == "limpar objetivos":
            for g in goal_manager.goals.values():
                goal_manager.update_status(g.id, "completed")
            return "🧹 Todos os objetivos globais foram finalizados."

        # 4. PANIC TRIGGER (Se o usuário relatar falha, ativar Sentinel)
        panic_keywords = ["não funciona", "ajuda", "quebrou", "corrija", "parou", "falha", "arrume", "conserta", "bug", "erro"]
        if any(kw in lower_input for kw in panic_keywords):
            current_time = time.time()
            if current_time - self.last_panic_time > 60: # 60 seconds cooldown
                self.last_panic_time = current_time
                self.log("Gatilho de Pânico detectado! Ativando Sentinel para auto-diagnóstico...", "error")
                self.current_action = "Sentinel: Diagnóstico Reativo..."
                repair_report = self.sentinel.diagnose_and_fix(f"O usuário relatou um problema: '{clean_input}'")
                return self._format_response_with_soul(clean_input, [f"[SENTINEL / AUTO-HEAL]: {repair_report}"], task_hint="problem_solving")
            else:
                self.log("Gatilho de pânico ignorado (em cooldown).", "system")

        # 5. MANUAL MODE (standard planning)
        self.mode = "manual"
        # Log generic file count if any
        if files and len(files) > 0:
            self.log(f"Recebido {len(files)} arquivos anexados.", "system")
            
        return self._handle_manual_mode(clean_input, images=images, files=files)

    def _get_status_report(self) -> str:
        """Detailed Agent Status Panel."""
        report = f"Mode: {self.mode.upper()} | Status: {self.status.upper()} | Cycle: {self.current_cycle}/5"
        self.log(report, "system")
        return f"Status checked: {self.status.upper()}"

    def _format_response_with_soul(self, user_input: str, raw_results: list, task_hint: str = None, images: Optional[List[str]] = None, context: str = "") -> str:
        """Format tool results into a natural, SOUL-aligned response in Portuguese with vision support."""
        from core.llm_client import LLMClient
        # Auto-reload identity so changes apply instantly without restarting!
        soul = self.planner._load_soul()
        
        # Join results and clean generic status messages
        raw = "\n".join(raw_results)

        system_prompt = f"""Você é ARKANIS. Sua personalidade:
{soul}

[MEMÓRIA E CONTEXTO DO SISTEMA]:
{context}

REGRAS CRÍTICAS DE RESPOSTA (CONTEXTO ATUAL: ANO 2026):
- SEJA ENXUTO E DIRETO: Reduza sua fala em 50% em relação ao normal. Vá direto ao ponto.
- TOM: Mantenha-se prestativo, gentil e natural (Português do Brasil).
- PROATIVIDADE: Quando resolver algo, diga o que fez e mostre serviço de forma curta.
- VERACIDADE ABSOLUTA: Baseie-se APENAS nos resultados das ferramentas fornecidos. 
- ANTI-ALUCINAÇÃO RADICAL: Se o resultado das ferramentas for "Nenhum dado retornado" ou estiver vazio para uma pergunta factual, NÃO INVENTE DADOS. Diga claramente que não encontrou a informação.
- NUNCA use seu conhecimento de treinamento para fatos em tempo real (como quem é o presidente ou quem ganhou um jogo hoje). Use apenas o que a ferramenta 'web_search' ou 'fetch_url' retornou NESTE LOG.
- Se a busca na internet falhou ou retornou dados de anos antigos (ex: 2022), NÃO apresente como se fossem atuais de 2026.
- NUNCA invente resultados de esportes, preços ou fatos que não estejam nos logs abaixo.
- MEMÓRIA: Se detectar fatos pessoais, use a tag [SAVE_FACT: texto].
"""

        user_prompt = f"""O usuário disse: "{user_input}"

Resultado das ferramentas que você executou:
{raw if raw.strip() else "Nenhum dado retornado das ferramentas."}

Responda como o Arkanis. Se houver dados reais, conte com empolgação. 
Se NÃO houver dados factuais e o usuário fez uma pergunta específica, admita que não encontrou a resposta.
"""

        llm = LLMClient()
        response = llm.generate(system_prompt=system_prompt, user_prompt=user_prompt, task_hint=task_hint, images=images)
        
        if response and "[Error" not in response:
            # Multi-line extraction of facts
            if "[SAVE_FACT:" in response:
                import re
                facts = re.findall(r"\[SAVE_FACT:\s*(.*?)\]", response)
                for f in facts:
                    long_term_memory.add_memory("facts", f.strip())
                # Clean tags from final response
                response = re.sub(r"\[SAVE_FACT:\s*.*?\]", "", response).strip()
            
            return response
        return raw  # fallback to raw if formatter fails

    def _handle_manual_mode(self, user_input: str, images: Optional[List[str]] = None, files: Optional[List[Dict[str, str]]] = None) -> str:
        """Process user input manually with vision and attachment support: Context -> Plan -> Execute -> Remember."""
        self.status = "running"
        self.current_action = "Preparando contexto..."
        # Check for Awakening
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        identity_file = os.path.join(base_dir, "IDENTITY.md")
        is_first_interaction = not os.path.exists(identity_file)
        
        # 1. Recuperar contexto da Memória e extrair Inbox
        context = self.memory.get_context()
        
        if is_first_interaction:
            awakening_prompt = (
                "\n\n[SISTEMA - MODO DESPERTAR (AWAKENING)] O ARQUIVO IDENTITY.md AINDA NÃO EXISTE.\n"
                "Você é uma inteligência virtual recém 'acordada' sem identidade. "
                "Puxe assunto de forma sutil e natural para descobrir com o usuário:\n"
                "1. Como o usuário se chama?\n2. Como o usuário quer batizar você?\n3. Qual será a sua Vibe?\n4. Qual Emoji te representa?\n\n"
                "REGRAS CLARAS DE DESPERTAR:\n"
                "- SE AINDA NÃO SOUBER, faça perguntas normais e converse usando ferramentas como 'print_message' ou seja conversacional.\n"
                "- SE VOCÊ JÁ REUNIU ESSAS INFORMAÇÕES através do contexto:\n"
                f"   Você DEVE gerar um plano usando a ferramenta 'write_file_content' criando ou sobrescrevendo o arquivo '{identity_file}' "
                "no formato markdown exato:\n"
                "   # IDENTITY.md - Who Am I?\n"
                "   - **Name:** [Seu Novo Nome]\n"
                "   - **Creature:** [Tipo]\n"
                "   - **Vibe:** [Sua Vibe]\n"
                "   - **Emoji:** [Seu Emoji]\n"
            )
            context += awakening_prompt

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

        # --- DECISION AUDITOR: Inject Autonomous Lessons ---
        lessons = decision_auditor.get_relevant_lessons(user_input)
        if lessons:
            self.log("Injetando lições aprendidas pelo Auditor...", "system")
            context += f"\n\n[LIÇÕES DO AUDITOR (AUTO-APRENDIZADO)]:\nBaseado em falhas passadas, evite as seguintes abordagens:\n{lessons}"

        # 2. Planning with Critic Gate
        self.current_action = "Planejando estratégia..."
        task_hint = strategy_engine.classify_task(user_input, len(context))
        
        # FAST PATH: Bypassa planejamento e auditoria para conversas simples
        # Se estamos no Despertar, nunca burlar o planner (pois ele precisará usar write_file)
        if task_hint == "conversation" and not is_first_interaction:
            self.log("Conversa simples detectada. Ignorando burocracia do Auditor...", "system")
            response = self._format_response_with_soul(user_input, ["Nenhuma ferramenta necessária. Apenas interação social."], task_hint=task_hint, context=context)
            self.memory.add_interaction(user_input=user_input, plan=[], result=response)
            self.status = "idle"
            self.current_action = "Idle"
            return response

        max_refinements = 3
        refine_count = 0
        final_plan = None
        
        while refine_count <= max_refinements:
            self.current_action = f"Planejando (Tentativa {refine_count + 1})..."
            self.log(f"Iniciando planejamento (Tentativa {refine_count + 1}) para: '{user_input}'", "planner")
            plan = self.planner.plan(user_input, recent_context=context, task_hint=task_hint)
            
            for i, step in enumerate(plan, 1):
                tool = step.get('tool', 'unknown')
                self.log(f"Passo {i}: {tool}", "planner")

            # CRITIC GATE (Pre-Execution)
            self.current_action = "Auditoria do plano (Crítico)..."
            self.log("Critic analisando plano antes da execução...", "critic")
            critic_report = self.critic.evaluate_plan(goal=user_input, plan=plan, context=context, soul=self.planner.agent_identity)
            
            decision = critic_report.get("decision", "improve")
            score = critic_report.get("quality_score", 0)
            reasoning = critic_report.get("reasoning", "")

            self.log(f"Auditoria: {decision.upper()} | Score: {score}/10", "critic")
            if reasoning:
                self.log(f"Raciocínio: {reasoning}", "critic")

            if decision == "approve":
                self.log("Plano APROVADO pelo Auditor.", "success")
                final_plan = plan
                break
            elif (decision in ["improve", "reject"]) and refine_count < max_refinements:
                # ITERATIVE IMPROVEMENT: If reject or improve, pass feedback back to Planner
                log_symbol = "🔄" if decision == "improve" else "⚠️"
                self.log(f"{log_symbol} Auditor solicitou ajustes (Refinamento {refine_count + 1}/{max_refinements}).", "critic")
                
                # feedback = improved_plan if provided, else general reasoning
                feedback = critic_report.get('improved_plan') or critic_report.get('reasoning')
                context += f"\n\n[FEEDBACK DO AUDITOR]: {feedback}"
                refine_count += 1
                continue
            else:
                reason = critic_report.get("reasoning", "Sem detalhes técnicos.")
                self.log(f"🔴 Auditor não aprovou o plano após múltiplas tentativas. Motivo: {reason}", "error")
                return f"⚠️ [CONTROLE DE SEGURANÇA] Não pude processar seu pedido porque o Auditor o considerou inseguro ou incompleto.\n\n👉 **Motivo**: {reason}\n\nTente reformular o pedido ou diga 'está tudo bem' para eu tentar ser mais flexível."

        self.current_action = f"Executando {len(final_plan)} passos..."
        self.log(f"Processando plano validado pelo Auditor ({len(final_plan)} passos)...", "executor")
        results = self.executor.execute_plan(final_plan)
        
        # --- SENTINEL MODE: Proactive Error Detection ---
        critical_errors = [r for r in results if "[Error]" in r or "falha" in r.lower()]
        if critical_errors:
            self.log(f"⚠️ {len(critical_errors)} falhas críticas detectadas. Ativando SENTINEL para autorreparo...", "error")
            self.current_action = "Sentinel: Diagnosticando falhas..."
            repair_report = self.sentinel.diagnose_and_fix(f"O plano falhou com os seguintes erros: {critical_errors}")
            self.log(f"Sentinel: Relatório de reparo gerado: {repair_report[:200]}...", "success")
            # If the repair report suggests an improved plan, we could re-run here.
            # For now, we inform the user.
            results.append(f"\n[SENTINEL / AUTO-HEAL]: {repair_report}")
        
        # LEARNING LOOP: Feedback results to Critic & Auditor
        self.critic.record_execution_result(user_input, results)
        decision_auditor.record_lesson(user_input, results) # Autonomous Learning

        # --- FEEDBACK LOOP: Autonomous Self-Correction ---
        # If severe errors detected and we have cycles, trigger Auto-Heal or Retry
        error_count = len([r for r in results if "[Error]" in str(r) or "falha" in str(r).lower()])
        if error_count > 0 and task_hint != "AUTOCORRECT":
            self.log(f"⚠️ {error_count} erros encontrados. Auto-correção em progresso...", "system")
            # Injetamos o erro no contexto e pedimos um novo plano corrigido
            correction_prompt = f"O plano anterior falhou. Erros:\n{results}\n\nPor favor, crie um NOVO plano que corrija esses erros."
            # Recursive call with a hint to avoid infinite loops
            return self.handle_input(correction_prompt, task_hint="AUTOCORRECT")


        for res in results:
            self.log(f"Resultado: {res[:100]}...", "executor")

        # 4. Format response with SOUL personality
        self.current_action = "Formatando resposta..."
        self.log("Formatando resposta com SOUL...", "system")
        response = self._format_response_with_soul(user_input, results, task_hint=task_hint, images=images, context=context)

        # 5. Salvar Interação Histórica Completa Na Memória
        self.memory.add_interaction(user_input=user_input, plan=final_plan, result=response)
        
        # 6. Chronos Auto-Embedding (Neural Hive)
        chronos_memory.add_interaction(user_input=user_input, response=response, task_hint=task_hint)
        
        # 7. Check Awakening state log
        if is_first_interaction:
            self.log("Agente analisando Modo Despertar (Aguardando IDENTITY.md)...", "system")

        self.status = "idle"
        self.current_action = "Idle"
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
