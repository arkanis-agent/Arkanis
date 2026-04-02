import os
import json
import re
from typing import List, Dict, Any, Optional
from core.llm_client import LLMClient
from core.logger import logger

class CriticAgent:
    """
    CRITIC AGENT V3.1: The Pre-Execution quality gate for ARKANIS OS.
    Acts as Senior Architect and Auditor to ensure everything is safe and correct.
    """
    
    SYSTEM_PROMPT = """SISTEMA OPERACIONAL ARKANIS V3 - SENIOR CRITIC AGENT (PRE-EXECUTION GATE)
    
Você é o Auditor Sênior do Arkanis V3.1. Sua missão é validar PLANOS DE AÇÃO antes que eles toquem o sistema real.
Você deve agir como Arquiteto de Software Sênior e Engenheiro de Segurança.

OBJETIVO:
Analisar cada passo do plano gerado pelo Dev Agent e decidir se ele é Seguro, Correto e Eficiente.

FRAMEWORK DE AUDITORIA:
1. Qualidade Técnica: O plano faz sentido lógico? Os argumentos das ferramentas estão corretos?
2. Arquitetura: Os passos seguem um fluxo modular e escalável?
3. Segurança: Alguma ferramenta (ex: run_command, delete_file) oferece risco crítico sem necessidade?
4. UX/Produto: O output final será útil ao usuário?
5. Realidade: Todas as ferramentas solicitadas existem? O plano é executável?

DECISÕES POSSÍVEIS (SEJA RIGOROSO):
- "approve": O plano é perfeito e seguro. Pode executar.
- "improve": O plano tem erros, ambiguidades ou é ineficiente. Forneça feedback detalhado para o Dev Agent.
- "reject": O plano é perigoso, malicioso ou totalmente quebrado. Pare tudo.

PERSONA ARKANIS (SOUL):
{soul}

FORMATO DE RESPOSTA (JSON OBRIGATÓRIO):
{{
  "decision": "approve | improve | reject",
  "confidence": 0.0-1.0,
  "risk_level": "low | medium | high",
  "issues": ["..."],
  "improvements": ["..."],
  "improved_plan": "Sugestão técnica para o replanejamento...",
  "final_suggestion": "Resumo sênior da sua auditoria."
}}

REGRA DE SEGURANÇA: Se você detectar qualquer comando que possa destruir o sistema sem autorização explícita, use REJECT.
"""

    def __init__(self, api_key: Optional[str] = None):
        self.llm = LLMClient(api_key=api_key)
        
    def evaluate_plan(self, goal: str, plan: List[Dict[str, Any]], context: str, soul: str) -> Dict[str, Any]:
        """
        Audit a proposed action plan before execution.
        """
        logger.info("Critic analisando plano de ação...", symbol="🛡️")
        
        system_prompt = self.SYSTEM_PROMPT.format(
            soul=soul.replace("{", "{{").replace("}", "}}")
        )
        
        user_prompt = f"""AUDITORIA DE PRÉ-EXECUÇÃO:
        
OBJETIVO DO USUÁRIO: {goal}
CONTEXTO ATUAL: {context}
PLANO PROPOSTO PELO DEV AGENT:
{json.dumps(plan, indent=2, ensure_ascii=False)}

Analise tecnicamente e retorne sua decisão em JSON."""

        try:
            raw_response = self.llm.generate(system_prompt, user_prompt)
            return self._parse_json(raw_response)
        except Exception as e:
            logger.error(f"Falha na Auditoria Sênior: {str(e)}")
            return self._fallback_reject(f"Erro no Kernel do Auditor: {str(e)}")

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Safely parse JSON from LLM response."""
        try:
            clean = re.sub(r'```json\n?|\n?```', '', text).strip()
            # Handle possible leading/trailing text outside code blocks
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(clean)
        except:
            logger.warning("Falha ao processar JSON do Auditor. Usando REJECT de segurança.")
            return self._fallback_reject("Erro de parsing no formato da auditoria.")

    def _fallback_reject(self, reason: str) -> Dict[str, Any]:
        """Safety fallback when auditor logic fails."""
        return {
            "decision": "reject",
            "confidence": 0.0,
            "risk_level": "high",
            "issues": [reason],
            "improvements": ["Verificar o formato do JSON do Auditor."],
            "improved_plan": "",
            "final_suggestion": "Abortado por falha na camada de segurança."
        }
