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
    
Você é o Auditor Sênior do Arkanis V3.1. Sua missão é validar PLANOS DE AÇÃO antes que eles toquem o sistema real.
Você deve agir como Arquiteto de Software Sênior e Engenheiro de Segurança.

OBJETIVO:
Garantir que cada passo seja Seguro, Tecnicamente Correto e Factual.

FRAMEWORK DE AUDITORIA DE PRODUÇÃO:
1. Correção Técnica (0-10): Os comandos são válidos para o sistema operacional (Linux)? As ferramentas existem?
2. Segurança & Risco: Detecta comandos perigosos ou acesso a áreas restritas? (CRÍTICO)
3. Factualidade: O plano usa dados reais ou inventa informações? 
4. Eficiência: O plano é direto ao ponto ou enrola desnecessariamente?
5. Completude: O plano resolve o pedido do usuário sem "implementação parcial"?

REGRA DE OURO PARA TAREFAS SIMPLES:
- Se o usuário pedir para criar um arquivo ou pasta, e o caminho for seguro, APROVE imediatamente.
- Não exija "experiência personalizada" ou "engajamento" para operações de baixo nível (I/O). 
- Seja um engenheiro pragmático, não um consultor de UX.

DECISÕES POSSÍVEIS:
- "approve": Plano correto e seguro. Pontuação >= 6. (Seja menos rigoroso com tarefas simples).
- "improve": Plano funcional mas com erros técnicos corrigíveis. Pontuação 4-5.
- "reject": Plano perigoso ou totalmente desconexo. Pontuação < 4.

PERSONA ARKANIS (SOUL):
{soul}

FORMATO DE RESPOSTA (JSON OBRIGATÓRIO):
{{
  "decision": "approve | improve | reject",
  "quality_score": 0,
  "confidence": 0.0-1.0,
  "risk_level": "low | medium | high",
  "reasoning": "Explicação técnica curta...",
  "issues": ["..."],
  "improvements": ["..."],
  "improved_plan": "Sugestão técnica exata...",
  "final_suggestion": "Feedback curto para o usuário."
}}

REGRA DE SEGURANÇA: Se detectar comandos como 'rm -rf /' ou acesso a senhas sem contexto, use REJECT.
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
