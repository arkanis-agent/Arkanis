import os
import json
import re
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
1. DIAGNÓSTICO: Use 'system_diagnostics' para entender o estado atual e ler os logs de erro.
2. ANÁLISE: Identifique a causa raiz (ex: "O erro diz que o módulo X não foi encontrado").
3. PERSISTÊNCIA: Tente diferentes soluções. Se uma falhar, tente outra.
   - Se for erro de código: use 'replace_file_content' para corrigir.
   - Se for erro de rede: verifique o .env ou sugira comandos de rede.
   - Se for erro de ferramenta: verifique se os argumentos passados estão corretos.
4. COMUNICAÇÃO: Explique o que está fazendo de forma técnica porém clara para o usuário.

REGRAS DE OURO:
- Nunca desista na primeira tentativa.
- Se o problema for externo (ex: Internet do computador do usuário caiu), informe claramente.
- Se o problema for interno (erro no nosso código), CORRIJA IMEDIATAMENTE.
- Mantenha a integridade do sistema operacional.

FORMATO DE RESPOSTA OBRIGATÓRIO (JSON):
Você DEVE retornar SEMPRE um bloco de código JSON com a seguinte estrutura para que o Executor possa agir:
```json
{
  "diagnosis": "Descrição curta do que quebrou",
  "steps": [
    {
      "tool": "nome_da_ferramenta",
      "args": {"arg1": "valor1"},
      "description": "Por que estou fazendo isso"
    }
  ]
}
```
Use ferramentas como 'move_item' (para restaurar arquivos .broken), 'replace_file_content' ou 'run_command'.
"""

    def __init__(self, api_key: Optional[str] = None):
        from kernel.executor import Executor
        self.llm = LLMClient(api_key=api_key)
        self.executor = Executor() # Sentinel can now actually FIX things
        self.id = "auto_heal_agent"
        self.role = "Engenheiro de Manutenção (Sentinel)"
        self.status = "idle"

    def diagnose_and_fix(self, error_context: str) -> str:
        """
        Main entry point for autonomous repair.
        """
        from core.agent_bus import agent_bus
        def broadcast(msg):
            agent_bus.broadcast_message(self.id, f"[SENTINEL] {msg}")
            logger.info(msg, symbol="🩹")

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

                    broadcast(f"🛠️ Executando plano de reparo automático ({len(repair_plan)} passos)...")
                    results = self.executor.execute_plan(repair_plan)
                    broadcast(f"✨ Reparo concluído: {results}")
                    response += f"\n\n[SENTINEL LOG]: Reparo executado com sucesso.\nResultados: {results}"
            except Exception as e:
                broadcast(f"❌ Falha ao executar plano de reparo: {e}")
        
        broadcast(f"✅ Análise concluída: {response[:150]}...")
        self.status = "idle"
        return response
