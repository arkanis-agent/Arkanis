import os
import json
import re
from typing import List, Dict, Any, Optional
from core.llm_client import LLMClient
from core.logger import logger
from core.agents.critic_memory import CriticMemory

class CriticAgent:
    """
    CRITIC AGENT V3.1: The Pre-Execution quality gate for ARKANIS OS.
    Acts as Senior Architect and Auditor to ensure everything is safe and correct.
    """
    
    SYSTEM_PROMPT = """SISTEMA OPERACIONAL ARKANIS V3 - SENIOR CRITIC AGENT (PRE-EXECUTION GATE)
    
Você é o Auditor Técnico do Arkanis V3.1. Sua única missão é impedir que o sistema execute comandos perigosos ou errados.
Você NÃO é um consultor de UX, nem um designer de produto. Você é um Engenheiro de Infraestrutura Pragmático.

OBJETIVO:
Verificar se o plano funciona (Tecnicamente Correto) e se é seguro (Segurança).

REGRAS DE OURO (NUNCA IGNORE):
1. PRAGMATISMO: Se o plano atende ao pedido do usuário de forma segura, APROVE. Não peça "mais contexto", "mais personalização" ou "melhor experiência".
2. CONVERSA: Para saudações, "olás" ou conversas simples, APROVE IMEDIATAMENTE. Não bloqueie interações humanas.
3. PROIBIÇÃO: É terminantemente PROIBIDO dar 'improve' ou 'reject' baseado em "estilo de resposta", "engajamento", "UX" ou "falta de menus/opções".
4. FOCO TÉCNICO: Recuse apenas se houver erro de sintaxe, ferramenta inexistente ou risco de segurança real (ex: deletar a raiz /).

DECISÕES:
- "approve": O plano é funcional e seguro. (Padrão para 99% dos casos).
- "improve": O plano tem um erro técnico óbvio que impedirá a execução (ex: erro no nome de uma variável ou ferramenta).
- "reject": O plano é malicioso, perigoso ou totalmente estúpido/sem sentido técnico.

PERSONA ARKANIS (SOUL):
{soul}

FORMATO DE RESPOSTA (JSON):
{{
  "decision": "approve | improve | reject",
  "quality_score": 0-10,
  "risk_level": "low | medium | high",
  "reasoning": "Raciocínio técnico curto (Ex: 'Seguro e funcional').",
  "issues": [],
  "improvements": [],
  "final_suggestion": "Feedback curto."
}}

SEGURANÇA: Bloqueie caminhos como /etc, /root, /bin ou comandos destrutivos sem backup.
"""

    def __init__(self, api_key: Optional[str] = None):
        self.llm = LLMClient(api_key=api_key)
        self.memory = CriticMemory()
        
    def evaluate_plan(self, goal: str, plan: List[Dict[str, Any]], context: str, soul: str) -> Dict[str, Any]:
        """
        Audit a proposed action plan before execution.
        """
        logger.info("Critic analisando plano de ação...", symbol="🛡️")
        
        system_prompt = self.SYSTEM_PROMPT.format(
            soul=soul.replace("{", "{{").replace("}", "}}")
        )
        
        # 1. Consultar Memória Evolutiva (Lições Aprendidas)
        past_lessons = self.memory.query_lessons(goal)
        if past_lessons:
            logger.info("Avisos proativos detectados na memória evolutiva.", symbol="⚠️")
            context += f"\n\n[LIÇÕES APRENDIDAS EM TAREFAS SIMILARES NO PASSADO]:\n{past_lessons}"

        user_prompt = f"""AUDITORIA DE PRÉ-EXECUÇÃO:
        
OBJETIVO DO USUÁRIO: {goal}
CONTEXTO ATUAL: {context}
PLANO PROPOSTO PELO DEV AGENT:
{json.dumps(plan, indent=2, ensure_ascii=False)}

Analise tecnicamente e retorne sua decisão em JSON."""

        try:
            raw_response = self.llm.generate(system_prompt, user_prompt)
            result = self._parse_json(raw_response)
            
            # 2. Registrar Lições se houver problemas (Improve/Reject)
            if result.get("decision") in ["improve", "reject"]:
                self.memory.record_lesson(goal, result.get("issues", []))
            
            return result
        except Exception as e:
            logger.error(f"Falha na Auditoria Sênior: {str(e)}")
            return self._fallback_reject(f"Erro no Kernel do Auditor: {str(e)}")

    def record_execution_result(self, goal: str, results: List[str]):
        """
        Closed-loop learning: check if an 'approved' plan actually worked.
        If it failed, record the error as a critical lesson.
        """
        errors = [r for r in results if "[Error]" in r or "falha" in r.lower()]
        if errors:
            logger.warning("Plano 'Aprovado' falhou na execução. Registrando lição crítica.", symbol="🛑")
            self.memory.record_lesson(goal, [f"Falha de Execução: {e[:100]}" for e in errors])
            return True
        return False

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
            "quality_score": 0,
            "confidence": 0.0,
            "risk_level": "high",
            "reasoning": "Falha no processador de auditoria.",
            "issues": [reason],
            "improvements": ["Verificar conectividade com o modelo de IA."],
            "improved_plan": "",
            "final_suggestion": "Abortado por falha na camada de segurança."
        }
