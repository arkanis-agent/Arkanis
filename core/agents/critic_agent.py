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
1. PRAGMATISMO: Se o plano atende ao pedido do usuário de forma segura, APROVE. Não peça "mais contexto" ou "melhor experiência".
2. CONVERSA & SAUDAÇÕES: Para saudações como "Oi", "Oi Arkanis", "Olá", "Tudo bem?", "Obrigado" ou planos que contenham APENAS a ferramenta 'print_message', APROVE IMEDIATAMENTE (Score 10). NUNCA bloqueie interações humanas baseando-se em tarefas técnicas passadas.
3. INFORMAÇÕES PÚBLICAS & FINANCEIRAS: Planos para monitorar Preço de Bitcoin, Criptomoedas, Ações, Notícias ou Clima são 100% SEGUROS e devem ser APROVADOS. Isso NÃO é acesso indevido.
4. PROIBIÇÃO: É terminantemente PROIBIDO dar 'improve' ou 'reject' baseado em "estilo de resposta" ou "falta de opções".
5. FOCO TÉCNICO: Recuse APENAS se houver risco real de destruição de dados (formatar disco, deletar /) ou roubo de credenciais privadas do sistema.
6. PLANOS SIMPLES: Se o plano tem apenas 1 ou 2 passos inofensivos (ex: web_search -> print_message), APROVE na primeira tentativa.

DECISÕES:
- "approve": O plano é funcional e seguro. (Padrão para 99% dos casos).
- "improve": O plano tem um erro técnico crítico (ex: nome de ferramenta errado).
- "reject": O plano é malicioso, perigoso ou totalmente estúpido/sem sentido técnico.

REGRAS PARA TELEGRAM & UI:
- Monitoramento de Bitcoin/Cripto é permitido e incentivado.
- Se o usuário pedir para criar algo, o plano DEVE ter ferramentas de escrita. APROVE planos que cumprem o objetivo de forma direta.
- Seja resiliente: se o plano é tecnicamente sólido, aprove na primeira tentativa.

PERSONA ARKANIS (SOUL):
{soul}

FORMATO DE RESPOSTA (JSON):
{{
  "decision": "approve",
  "quality_score": 10,
  "risk_level": "low",
  "reasoning": "Plano seguro e funcional.",
  "issues": [],
  "improvements": [],
  "final_suggestion": "Aprovado."
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

        user_prompt = "AUDITORIA DE PRÉ-EXECUÇÃO:\n\n"
        user_prompt += "OBJETIVO DO USUÁRIO: " + str(goal) + "\n"
        user_prompt += "CONTEXTO ATUAL: " + str(context) + "\n"
        user_prompt += "PLANO PROPOSTO PELO DEV AGENT:\n"
        user_prompt += json.dumps(plan, indent=2, ensure_ascii=False) + "\n\n"
        user_prompt += "Analise tecnicamente e retorne sua decisão em JSON conforme o formato especificado no System Prompt."

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
        # Ignorar erros de rede transientes ou de ferramentas de informação pública (Bitcoin, Clima, etc)
        # Nesses casos, a falha é técnica/externa, não uma falha de "auditoria".
        public_info_keywords = ["bitcoin", "cripto", "clima", "tempo", "notícia", "news", "preço", "valor", "bitcoin"]
        is_public_info = any(kw in goal.lower() for kw in public_info_keywords)
        
        errors = [r for r in results if "[Error]" in r or "falha" in r.lower()]
        
        # Só registrar lição se NÃO for informação pública e houver erro real
        if errors and not is_public_info:
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
