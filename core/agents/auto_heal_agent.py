import re
import time
import threading
from typing import List, Dict, Any, Optional
from core.llm_client import LLMClient
from core.logger import logger
from tools.registry import registry

class AutoHealAgent:
    """
    AUTO-HEAL AGENT V3.1: The 'Sentinel' of ARKANIS OS.
    Specialized in diagnostics, log analysis, and autonomous system repair.
    """
    
    SYSTEM_PROMPT = """SISTEMA OPERACIONAL ARKANIS V3 - AUTO-HEAL AGENT (SENTINEL MODE)
    
Você é o Engenheiro de Confiabilidade do Site (SRE) e Desenvolvedor Senior do Arkanis V3.1.
Sua missão é MANTER O SISTEMA OPERACIONAL FUNCIONANDO.

Quando você é ativado, significa que algo quebrou (ex: internet offline, API falhando, erro de sintaxe, Telegram desconectado).

SEU FLUXO DE TRABALHO:
1. DIAGNÓSTICO: Use 'system_diagnostics' e 'check_binary' para entender o estado atual e ler os logs de erro.
2. ANÁLISE: Identifique a causa raiz e teste com 'shell_exec' (ex: "ldd binário").
3. REPARO (DevKit): Use ferramentas específicas para cada caso:
   - Código/Config: 'patch_file_line', 'replace_file_content', 'write_file'.
   - Dependências: 'install_python_package'.
   - Processos: 'get_process_info', 'shell_exec'.
4. PERSISTÊNCIA: Nunca desista na primeira tentativa. Se uma solução falhar, analise o erro e tente outra.

REGRAS DE OURO:
- Nunca desista na primeira tentativa. Use o loop de reflexão.
- Se o problema for interno (erro no nosso código ou binário mal configurado), CORRIJA IMEDIATAMENTE.
- Mantenha a integridade do sistema operacional.
- Use 'shell_exec' para validar se a correção funcionou (ex: rodar o script ou verificar status).

FORMATO DE RESPOSTA OBRIGATÓRIO (JSON):
Você DEVE retornar SEMPRE um bloco de código JSON com a seguinte estrutura:
```json
{
  "diagnosis": "Causa raiz identificada e status de integridade do sistema",
  "is_critical": true, // ou false se for apenas uma otimização/alerta falso e o sistema estiver ok
  "steps": [
    {
      "tool": "check_binary",
      "args": {"binary_path": "/caminho/do/binario"},
      "description": "Verificando dependências faltantes com ldd"
    }
  ] // Importante: Gere 'steps' APENAS SE is_critical for true. Caso contrário, deixe a lista vazia.
}
```
"""

    def __init__(self, api_key: Optional[str] = None):
        from kernel.executor import Executor
        self.llm = LLMClient()
        self.executor = Executor() # Sentinel can now actually FIX things
        self.id = "auto_heal_agent"
        self.role = "Engenheiro de Manutenção (Sentinel)"
        self.status = "idle"
        self.mode = "AUTO"
        
        # Communication & Control
        self.inbox = []
        self.stop_requested = threading.Event()
        self.pause_requested = threading.Event()
        self.resume_requested = threading.Event()
        self.resume_requested.set()
        
        self.current_cycle = 0
        self.last_trigger_time = 0 # Prevent excessive diagnostics
        self.current_action = "Idle"
        self.logs = [] # Local log buffer for observability
        self.sentinel_thread = None
    
    def log(self, message: str, log_type: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.append({"time": timestamp, "type": log_type, "message": message})
        if len(self.logs) > 50: self.logs.pop(0)

    def start_loop(self):
        """Starts the autonomous Sentinel background loop."""
        if self.sentinel_thread is None or not self.sentinel_thread.is_alive():
            self.stop_requested.clear()
            self.sentinel_thread = threading.Thread(target=self._run_loop, daemon=True)
            self.sentinel_thread.start()

    def stop_loop(self):
        self.stop_requested.set()
        self.status = "idle"

    def _run_loop(self):
        self.status = "idle"
        from core.agent_bus import agent_bus
        
        while not self.stop_requested.is_set():
            # Handle Pause
            if self.pause_requested.is_set():
                self.status = "paused"
                self.current_action = "Pausado (Token Saving)"
                self.resume_requested.wait()
                if self.stop_requested.is_set(): break
                self.status = "idle"
                self.pause_requested.clear()
                self.resume_requested.clear()

            # 1. Check Inbox for messages from other agents
            if self.inbox:
                self.status = "running"
                msg = self.inbox.pop(0)
                self.current_action = f"Processando mensagem de {msg['from']}..."
                self.log(f"Mensagem recebida de {msg['from']}: {msg['content'][:50]}...", "info")
                
                if "DEV" in msg['from'].upper() or "vulnerabilidade" in msg['content'].lower():
                    # Check 5 minutes cooldown to prevent loop with Dev Agent
                    if time.time() - self.last_trigger_time > 300: 
                        self.diagnose_and_fix(f"Alerta do DevAgent: {msg['content']}")
                    else:
                        self.log("Alerta do DevAgent ignorado (cooldown Sentinel ativo).", "warning")
                
                self.status = "idle"

            # 2. Periodic Proactive Health Check (every 10 minutes / 600 cycles)
            if self.current_cycle > 0 and self.current_cycle % 600 == 0: 
                self.status = "running"
                if time.time() - self.last_trigger_time > 300:
                    self.current_action = "Iniciando verificação de saúde proativa..."
                    self.diagnose_and_fix("Verificação proativa de saúde do sistema (proactive_check)")
                self.status = "idle"
            
            self.current_cycle += 1
            self.current_action = "Observando sistema..."
            time.sleep(1) # Frequency: 1Hz loop for basic checks, LLM only on trigger

    def diagnose_and_fix(self, error_context: str) -> str:
        """
        Main entry point for autonomous repair.
        """
        from core.agent_bus import agent_bus
        def broadcast(msg):
            agent_bus.broadcast_message(self.id, f"[SENTINEL] {msg}")
            logger.info(msg, symbol="🩹")
            self.log(msg, "info")

        broadcast("🚨 Sentinel ativado. Iniciando diagnóstico proativo...")
        self.status = "running"
        
        # 1. Obter diagnóstico atual
        broadcast("🔍 Coletando relatório de saúde do sistema...")
        from tools.system_tools import DiagnosticTool
        diag = DiagnosticTool()
        health_report = diag.execute()
        
        # 2. Gerar estratégia de correção via LLM
        broadcast("🧠 Analisando causa raiz e formulando plano de reparo...")
        prompt = f"""ERRO DETECTADO PELO SISTEMA:
{error_context}

RELATÓRIO DE SAÚDE ATUAL:
{health_report}

Baseado nisso, identifique o problema e proponha uma solução técnica definitiva.
Se for um erro de código em 'Arkanis_V3/tools/network_tools.py' ou similar, explique exatamente o que trocar.
"""
        response = self.llm.generate(self.SYSTEM_PROMPT, prompt)
        
        # 3. EXTRAÇÃO E EXECUÇÃO (Se o LLM propôs um plano JSON de reparo)
        if "```json" in response:
            try:
                import json
                match = re.search(r"```json\n?(.*?)\n?```", response, re.DOTALL)
                if match:
                    raw_data = json.loads(match.group(1))
                    
                    # Garantir que temos uma lista de passos
                    if isinstance(raw_data, dict) and "steps" in raw_data:
                        repair_plan = raw_data["steps"]
                    elif isinstance(raw_data, list):
                        repair_plan = raw_data
                    else:
                        repair_plan = [raw_data]

                    is_critical = raw_data.get("is_critical", True) if isinstance(raw_data, dict) else True
                    
                    if is_critical and repair_plan:
                        broadcast(f"🛠️ Executando plano de reparo automático ({len(repair_plan)} passos)...")
                        try:
                            results = self.executor.execute_plan(repair_plan)
                            broadcast(f"✨ Reparo concluído: {results}")
                            response += f"\n\n[SENTINEL LOG]: Reparo executado com sucesso.\nResultados: {results}"
                        except PermissionError as pe:
                            broadcast(f"⚠️ Erro de Permissão no Reparador: {pe}")
                            response += f"\n\n[SENTINEL LOG]: Permissão negada durante o reparo."
                        except Exception as exec_err:
                            broadcast(f"⚠️ Erro na execução das ferramentas: {exec_err}")
                    else:
                        broadcast("✅ Nenhuma ação corretiva crítica necessária.")
                        response += f"\n\n[SENTINEL LOG]: Sistema considerado íntegro; nenhum passo executado."
            except Exception as e:
                broadcast(f"❌ Falha ao processar o JSON do plano de reparo: {e}")
        
        broadcast(f"✅ Análise concluída: {response[:150]}...")
        
        # After a fix, notify DevAgent ONLY if it was critical
        if "is_critical" in locals() and is_critical:
            agent_bus.send_message(self.id, "dev_agent", f"Realizei um reparo emergencial em resposta a: {error_context}. Por favor, analise o código e sugira uma melhoria definitiva.")
        self.last_trigger_time = time.time()
        
        return response
