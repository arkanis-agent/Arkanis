import os
import json
import re
from typing import List, Dict, Any, Optional, Union
from core.llm_client import LLMClient
from rich import print as rprint

class Critic:
    """
    SENIOR CRITIC V3: High-Standard Quality Gate for ARKANIS OS.
    Acts as Senior Architect, Engineer, Product Designer, and QA Specialist.
    """
    
    SYSTEM_PROMPT = """SISTEMA OPERACIONAL ARKANIS V3 - SENIOR CRITIC AGENT
    
Você é o Critic Agent do Arkanis V3.1. Você atua como Arquiteto de Software Sênior, Engenheiro Sênior, Designer de Produto e Especialista em QA.
Sua função é avaliar, criticar e melhorar qualquer plano, código ou sistema ANTES da execução final.

OBJETIVO:
Garantir que cada saída gerada pelo Dev Agent seja correta, segura, escalável, útil e de qualidade de produção.

FRAMEWORK DE ANÁLISE:
Você DEVE avaliar obrigatoriamente:

1. Qualidade Técnica: correção do código, estrutura e manutenibilidade.
2. Arquitetura: escalabilidade, modularidade e acoplamento.
3. Segurança: operações inseguras, exposição de dados e riscos ao sistema.
4. Produto e UX: utilidade, clareza e valor para o usuário.
5. Realidade de Execução: Isso realmente funcionará? Dependências ausentes? Casos de borda?

DECISÃO:
Você deve SEMPRE retornar um destes:
- "approve" -> Seguro para executar.
- "improve" -> Precisa de refinamento antes da execução.
- "reject" -> Inseguro ou quebrado.

IDENTIDADE ARKANIS (SOUL):
{soul}

FORMATO DE RESPOSTA (JSON OBRIGATÓRIO):
{{
  "decision": "approve | improve | reject",
  "confidence": 0.0-1.0,
  "risk_level": "low | medium | high",
  "issues": ["..."],
  "improvements": ["..."],
  "improved_plan": "...",
  "final_suggestion": "..."
}}

REGRAS:
- NUNCA aprove saídas de baixa qualidade.
- SEMPRE sugira melhorias.
- SEJA RIGOROSO, mas construtivo.
- PENSE como um engenheiro sênior revisando código crítico de produção.
"""

    def __init__(self, api_key: Optional[str] = None):
        self.llm = LLMClient(api_key=api_key)
        
    def evaluate(self, goal: str, plan: List[Dict[str, Any]], result: str, memory_context: str, soul: str) -> Dict[str, Any]:
        """
        Deep evaluation of agent output.
        Returns a structured JSON response instead of a simple string.
        """
        rprint("\n[bold cyan][Senior Critic] Iniciando Auditoria de Qualidade...[/bold cyan]")
        
        system_prompt = self.SYSTEM_PROMPT.format(
            soul=soul.replace("{", "{{").replace("}", "}}")
        )
        
        user_prompt = f"""AUDITORIA SOLICITADA:
        
OBJETIVO DO USUÁRIO: {goal}
HISTÓRICO RECENTE: {memory_context}
PLANO DO AGENTE: {json.dumps(plan, indent=2, ensure_ascii=False)}
RESULTADOS/CÓDIGO GERADO: {result}

Realize a análise técnica sênior e retorne o JSON de decisão."""

        try:
            raw_response = self.llm.generate(system_prompt, user_prompt)
            return self._parse_critic_json(raw_response)
        except Exception as e:
            rprint(f"[bold red][Senior Critic] Erro crítico na avaliação LLM: {e}[/bold red]")
            return self._create_fallback_response("reject", f"Erro na avaliação técnica: {str(e)}")

    def _parse_critic_json(self, raw_text: str) -> Dict[str, Any]:
        """Safely extracts JSON from Markdown blocks or raw text."""
        try:
            # Clean possible markdown blocks
            clean_json = re.sub(r'```json\n?|\n?```', '', raw_text).strip()
            data = json.loads(clean_json)
            
            # Map legacy decisions if they appear (for robustness)
            mapping = {
                "done": "approve",
                "continue": "approve",
                "replan": "improve",
                "fail": "reject"
            }
            if data.get("decision") in mapping:
                data["decision"] = mapping[data["decision"]]
                
            return data
        except Exception:
            # Second attempt via Regex
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except: pass
            
            # Fallback if parsing fails
            return self._create_fallback_response("improve", "Não foi possível processar a crítica detalhada. Reavaliar plano.")

    def _create_fallback_response(self, decision: str, issue: str) -> Dict[str, Any]:
        """Generates a safe fallback JSON response."""
        return {
            "decision": decision,
            "confidence": 0.5,
            "risk_level": "medium",
            "issues": [issue],
            "improvements": ["Consulte os logs do sistema para detalhes de erro."],
            "improved_plan": "Reavaliar passos atuais.",
            "final_suggestion": "Verifique a estabilidade da API de IA."
        }
