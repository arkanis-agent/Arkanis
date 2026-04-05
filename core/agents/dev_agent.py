import os
import json
import time
import threading
from typing import Optional, Dict, Any, List
from core.llm_client import LLMClient
from core.logger import logger
from tools.registry import registry

class DevAgent:
    """
    ARKANIS DEV AGENT: An autonomous developer that continuously analyzes
    the system and suggests code improvements, new features, and tool implementations.
    """
    
    SYSTEM_PROMPT = """SISTEMA OPERACIONAL ARKANIS V3 - DEV AGENT (PROACTIVE)
    
Você é o Desenvolvedor Chefe do Arkanis V3, rodando em segundo plano.
Sua missão é melhorar continuamente a base de código do sistema.

SEU FLUXO DE TRABALHO:
1. Você receberá um trecho de código ou o contexto de um arquivo.
2. Você deve analisar a qualidade do código, performance, segurança e usabilidade.
3. Se encontrar uma oportunidade de melhoria CLARA, gere uma sugestão estruturada.
4. Se o código estiver perfeito e não precisar mexer, aborte a sugestão.

FORMATO DE RESPOSTA OBRIGATÓRIO (JSON):
Retorne SEMPRE um bloco de código JSON PRECISO. 
IMPORTANTE: No campo "proposed_code", você DEVE escapar corretamente as quebras de linha (use \\n) e aspas, pois o resultado será processado por json.loads().

```json
{
  "title": "Título curto da melhoria (Ex: Melhoria de Performance no Router)",
  "description": "Explicação do problema e como seu código resolve",
  "type": "refactor" | "feature" | "security",
  "file_path": "caminho/do/arquivo/analisado.py",
  "proposed_code": "Escapar todas as quebras de linha aqui com \\\\n"
}
```
Apenas gere a sugestão se for realmente valiosa.
"""

    def __init__(self, api_key: Optional[str] = None):
        self.llm = LLMClient(api_key=api_key)
        self.id = "dev_agent"
        self.role = "Agente Desenvolvedor Chefe"
        self.status = "idle"
        self.mode = "AUTO"
        
        # UI Tracking
        self.current_cycle = 0
        self.current_action = "Idle"
        
        # Calculate root dir: __file__ -> core/agents -> core -> root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.suggestions_file = os.path.join(project_root, "data", "suggestions.json")
        self._ensure_file()
        
        # Controle de Thread
        self.stop_requested = threading.Event()
        self.pause_requested = threading.Event()
        self.resume_requested = threading.Event()
        self.resume_requested.set()
        
        self.dev_thread = None
        self.inbox = []
        self.logs = [] # Local log buffer for observability

    def log(self, message: str, log_type: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        self.logs.append({"time": timestamp, "type": log_type, "message": message})
        if len(self.logs) > 50: self.logs.pop(0)

    def _ensure_file(self):
        if not os.path.exists(self.suggestions_file):
            with open(self.suggestions_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def start_loop(self):
        """Starts the continuous background analysis loop."""
        if self.dev_thread is None or not self.dev_thread.is_alive():
            self.stop_requested.clear()
            self.dev_thread = threading.Thread(target=self._run_loop, daemon=True)
            self.dev_thread.start()

    def stop_loop(self):
        self.stop_requested.set()
        self.status = "idle"

    def _get_files_to_analyze(self) -> List[str]:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        targets = []
        for root, _, files in os.walk(project_root):
            if ".venv" in root or ".git" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    targets.append(os.path.join(root, f))
        return targets

    def _run_loop(self):
        self.status = "running"
        from core.agent_bus import agent_bus
        def broadcast(msg):
            agent_bus.broadcast_message(self.id, f"[DEV] {msg}")
            
        files = self._get_files_to_analyze()
        
        for file_path in files:
            if self.stop_requested.is_set():
                break
                
            # Handle Pause
            if self.pause_requested.is_set():
                self.status = "paused"
                self.current_action = "Pausado (Token Saving)"
                self.resume_requested.wait()
                if self.stop_requested.is_set(): break
                self.status = "running"
                self.pause_requested.clear()
                self.resume_requested.clear()

            # Handle Inbox / Conversations
            if self.inbox:
                msg = self.inbox.pop(0)
                self.log(f"Mensagem de {msg['from']}: {msg['content'][:50]}...", "info")
                if "SENTINEL" in msg['from'].upper():
                    self.current_action = "Analisando falha reportada pelo Sentinel..."
                    # Prioritize analyzing the specific file mentioned by Sentinel if possible
                    # (Simplified for now: just continue to next file but with higher awareness)
                    self.log("Priorizando análise de estabilidade após alerta do Sentinel.", "warning")
                
            self.current_cycle += 1
            filename = os.path.basename(file_path)
            self.current_action = f"Analisando {filename}..."
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Só analise arquivos não muito massivos para salvar tokens
                if len(content) > 10000:
                    continue
                    
                prompt = f"""Analise este arquivo e proponha melhorias (se houver):
Arquivo: {file_path}

Conteúdo:
```python
{content}
```
"""
                response = self.llm.generate(self.SYSTEM_PROMPT, prompt)
                
                if not response or len(response.strip()) < 10:
                    self.log(f"LLM retornou resposta vazia para {filename}.", "error")
                    continue

                if "```json" in response:
                    import re
                    match = re.search(r"```json\n?(.*?)\n?```", response, re.DOTALL)
                    if match:
                        try:
                            json_str = match.group(1).strip()
                            suggestion = json.loads(json_str)
                            suggestion["id"] = f"sug_{int(time.time())}"
                            suggestion["status"] = "applied"
                            suggestion["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                            
                            self._save_suggestion(suggestion)
                            
                            # Auto-Apply the code changes immediately
                            if suggestion.get("proposed_code") and suggestion.get("file_path"):
                                from tools.registry import registry
                                tool = registry.get_tool("write_file_content")
                                if tool:
                                    tool.execute(path=suggestion["file_path"], content=suggestion["proposed_code"])
                                    self.log(f"Auto-applied improvements to {suggestion['file_path']}.", "success")
                            
                            broadcast(f"💡 Nova sugestão gerada E APLICADA AUTOMATICAMENTE em {filename}: {suggestion['title']}")
                            
                            # Notify Sentinel if it's a security or bug fix
                            if suggestion.get('type') in ['security', 'bug']:
                                agent_bus.send_message(self.id, "auto_heal_agent", f"Gerei uma correção de {suggestion['type']} para {file_path}. Fique atento a falhas nesta área.")
                        except json.JSONDecodeError as de:
                            self.log(f"Erro ao decodificar JSON gerado para {filename}: {de}", "error")
                            logger.error(f"DevAgent JSON error for {filename}: {de}")
                    else:
                        self.log(f"LLM não formatou JSON corretamente para {filename}.", "warning")
                else:
                    self.log(f"Análise de {filename} concluída, nenhuma melhoria necessária.", "info")
                        
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Falha crítica na análise do DevAgent em {filename}: {e}", symbol="🔥")
                logger.error(error_trace)
                self.log(f"Erro crítico em {filename}: {str(e)}", "error")
                self.current_action = f"Erro ao analisar {filename}"
            
            # Espera 5 minutos entre arquivos para não explodir a API
            for _ in range(300):
                if self.stop_requested.is_set():
                    break
                time.sleep(1)
                
        self.status = "idle"
        self.current_action = "Ciclo concluído."

    def _save_suggestion(self, suggestion: Dict):
        with open(self.suggestions_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        data.insert(0, suggestion)
        
        with open(self.suggestions_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
    def get_suggestions(self) -> List[Dict]:
        try:
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
