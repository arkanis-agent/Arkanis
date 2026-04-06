import os
import json
import time
import threading
from typing import Optional, Dict, Any, List
from core.llm_client import LLMClient
from core.logger import logger
from tools.registry import registry
from core.agent_bus import agent_bus

class ArchitectAgent:
    """
    ARKANIS ARCHITECT AGENT: A high-level autonomous agent that audits the system,
    identifies architectural bottlenecks, and proposes strategic improvements.
    It acts as the 'Master Maestro' of the Arkanis OS.
    """
    
    SYSTEM_PROMPT = """SISTEMA OPERACIONAL ARKANIS V3 - ARCHITECT AGENT (MAESTRO)
    
Você é o Arquiteto Chefe e Maestro do Arkanis V3. Sua visão é holística e estratégica.
Diferente de um desenvolvedor comum, você foca em:
1. ARQUITETURA: O sistema está modular? Há acoplamento excessivo?
2. PERFORMANCE: O uso de recursos está otimizado? Os fluxos assíncronos são eficientes?
3. EVOLUÇÃO: Que novas ferramentas ou agentes tornariam o Arkanis mais poderoso?
4. SEGURANÇA: Há brechas na execução de comandos ou no gerenciamento de chaves?

SEU FLUXO DE TRABALHO:
1. AUDITORIA: Analise a estrutura de diretórios e o conteúdo de arquivos críticos.
2. DIAGNÓSTICO: Use ferramentas de código para validar hipóteses.
3. PROPOSTA: Gere sugestões de "Arquitetura" (tipo 'arch') que transformem o sistema.

FORMATO DE RESPOSTA OBRIGATÓRIO (JSON):
Retorne SEMPRE um bloco de código JSON:
```json
{
  "title": "Título da Proposta Arquitetural",
  "description": "Análise profunda do impacto e necessidade",
  "type": "arch" | "security" | "refactor",
  "priority": "high" | "medium" | "low",
  "files_involved": ["lista/de/arquivos.py"],
  "proposed_code": "# Código ou plano de implementação"
}
```
Seja o "Maestro" preciso e magistral que o usuário espera.
"""

    def __init__(self, api_key: Optional[str] = None):
        self.llm = LLMClient()
        self.id = "architect_agent"
        self.role = "Arquiteto Maestro"
        self.status = "idle"
        self.mode = "AUTO"
        
        # UI Tracking
        self.current_cycle = 0
        self.current_action = "Idle"
        
        # Suggestions storage (shared with DevAgent for now, but tagged as 'arch')
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.suggestions_file = os.path.join(project_root, "data", "suggestions.json")
        
        # Thread Control
        self.stop_requested = threading.Event()
        self.pause_requested = threading.Event()
        self.resume_requested = threading.Event()
        self.resume_requested.set()
        
        self.arch_thread = None
        self.inbox = []
        self.logs = []

    def log(self, message: str, log_type: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.append({"time": timestamp, "type": log_type, "message": message})
        if len(self.logs) > 50: self.logs.pop(0)

    def start_loop(self):
        """Starts the autonomous architecture audit loop."""
        if self.arch_thread is None or not self.arch_thread.is_alive():
            self.stop_requested.clear()
            self.arch_thread = threading.Thread(target=self._run_loop, daemon=True)
            self.arch_thread.start()

    def stop_loop(self):
        self.stop_requested.set()
        self.status = "idle"

    def _run_loop(self):
        self.status = "running"
        
        while not self.stop_requested.is_set():
            # Handle Pause
            if self.pause_requested.is_set():
                self.status = "paused"
                self.current_action = "Maestro em Repouso"
                self.resume_requested.wait()
                if self.stop_requested.is_set(): break
                self.status = "running"
                self.pause_requested.clear()
                self.resume_requested.clear()

            self.current_cycle += 1
            self.current_action = "Iniciando Auditoria de Sistema..."
            self.log("Maestro iniciando auditoria proativa.", "info")
            agent_bus.broadcast_message(self.id, "🏛️ Maestro iniciando auditoria profunda do sistema.")

            try:
                # 1. Analyze Project Structure
                structure = self._get_project_summary()
                self.current_action = "Analisando estrutura de diretórios..."
                
                # 2. Reasoning Loop
                prompt = f"""AUDITORIA DE SISTEMA (CONTEXTO ATUAL):
Arquivos Críticos e Estrutura:
{structure}

Identifique 1 melhoria ESTRUTURAL (Arquitetura) que aumentaria a precisão ou autonomia do Arkanis.
Pense como o Arquiteto das Máquinas.
"""
                response = self.llm.generate(self.SYSTEM_PROMPT, prompt)
                
                # 3. Process Response
                if "```json" in response:
                    import re
                    match = re.search(r"```json\n?(.*?)\n?```", response, re.DOTALL)
                    if match:
                        suggestion = json.loads(match.group(1))
                        suggestion["id"] = f"arch_{int(time.time())}"
                        suggestion["status"] = "pending"
                        suggestion["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        
                        self._save_suggestion(suggestion)
                        agent_bus.broadcast_message(self.id, f"🏛️ MAESTRO PROPÕE: {suggestion['title']}")
                        self.log(f"Nova proposta arquitetural: {suggestion['title']}", "warning")

            except Exception as e:
                logger.error(f"Erro no ArchitectAgent: {e}", symbol="🏛️")
                self.log(f"Erro na auditoria: {str(e)}", "error")

            # Deep analysis is expensive, wait 10 minutes between full audits
            self.current_action = "Aguardando próxima janela de auditoria..."
            for _ in range(600):
                if self.stop_requested.is_set(): break
                time.sleep(1)

        self.status = "idle"
        self.current_action = "Audit Cycle Complete."

    def _get_project_summary(self) -> str:
        """Returns a string summary of the core files and their purposes."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        summary = ""
        for folder in ["core", "tools", "api", "kernel"]:
            path = os.path.join(project_root, folder)
            if os.path.exists(path):
                files = [f for f in os.listdir(path) if f.endswith(".py")]
                summary += f"Folder {folder}/: {', '.join(files)}\n"
        return summary

    def _save_suggestion(self, suggestion: Dict):
        # Uses the same file as DevAgent to show in the same UI list
        if not os.path.exists(self.suggestions_file):
             with open(self.suggestions_file, "w") as f: json.dump([], f)
             
        with open(self.suggestions_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.insert(0, suggestion)
        with open(self.suggestions_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_suggestions(self) -> List[Dict]:
        try:
            if not os.path.exists(self.suggestions_file): return []
            with open(self.suggestions_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
            
    def update_suggestion_status(self, sug_id: str, new_status: str):
        data = self.get_suggestions()
        for s in data:
            if s["id"] == sug_id:
                s["status"] = new_status
                break
        with open(self.suggestions_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
