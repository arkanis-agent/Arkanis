import os
import json
from typing import List, Dict, Any, Optional
from core.llm_client import LLMClient
from rich import print as rprint

class Critic:
    """
    CRITIC V3: Self-Reflection Layer for ARKANIS OS.
    Evaluates actions against the objective and identity.
    """
    
    EVALUATION_PROMPT = """SISTEMA OPERACIONAL ARKANIS V3 - CAMADA DE CRÍTICA (SELF-REFLECTION)

Você é o Juiz de Avaliação do ARKANIS V3. Sua única função é analisar se as ações recentes nos levam ao objetivo final.

IDENTIDADE (SOUL):
{soul}

CONTEXTO RECENTE:
{memory}

OBJETIVO:
{goal}

PLANO EXECUTADO:
{plan}

RESULTADO:
{result}

REGRAS OBRIGATÓRIAS:
Responda APENAS com uma destas quatro palavras-chave, sem formatação, sem markdown, sem explicações:
- "done" -> o objetivo foi claramente e totalmente atingido.
- "continue" -> progresso correto, pode continuar no próximo passo planejado.
- "replan" -> plano inadequado, precisa de novos passos ou deu erro.
- "fail" -> erro crítico, objetivo impossível de prosseguir.
"""

    def __init__(self, api_key: Optional[str] = None):
        self.llm = LLMClient(api_key=api_key)
        
    def evaluate(self, goal: str, plan: List[Dict[str, Any]], result: str, memory_context: str, soul: str) -> str:
        rprint("\n[bold cyan][Critic] Avaliando resultado...[/bold cyan]")
        
        system_prompt = self.EVALUATION_PROMPT.format(
            soul=soul.replace("{", "{{").replace("}", "}}"),
            memory=memory_context,
            goal=goal,
            plan=json.dumps(plan, ensure_ascii=False),
            result=result
        )
        
        raw_response = self.llm.generate(system_prompt, "Avalie e responda APENAS com a palavra de decisão.")
        
        if not raw_response:
            return self._fallback_logic(plan, result)
            
        decision = raw_response.strip().lower()
        
        valid_decisions = ["done", "continue", "replan", "fail"]
        for d in valid_decisions:
            if d in decision:
                rprint(f"[bold cyan][Critic] Decisão: {d}[/bold cyan]")
                return d
                
        return self._fallback_logic(plan, result)
        
    def _fallback_logic(self, plan: List[Dict[str, Any]], result: str) -> str:
        """Heuristic simple self-reflection when LLM is unavailable."""
        rprint("[bold cyan][Critic] Decisão executada via FALLBACK (Sem API).[/bold cyan]")
        
        if "error" in result.lower() or "erro" in result.lower() or "falha" in result.lower():
            if len(plan) > 0 and plan[0].get("tool") == "print_message":
                return "fail"
            return "replan"
            
        if len(plan) == 1 and plan[0].get("tool") == "print_message":
            return "done"
            
        return "continue"
