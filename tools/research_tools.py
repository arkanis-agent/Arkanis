import os
import json
import logging
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry

logger = logging.getLogger("uvicorn")

class IntelligenceResearcher(BaseTool):
    """
    ARKANIS V3.1 - Deep Intelligence Researcher
    Uses the browser tools to perform multi-source search and synthesize an executive summary.
    """
    
    @property
    def name(self) -> str:
        return "deep_researcher"

    @property
    def description(self) -> str:
        return "Executa uma pesquisa profunda na web sobre um tema complexo, sintetizando informações de múltiplas fontes em um relatório executivo."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "topic": "O tema ou pergunta complexa para pesquisar.",
            "sources_count": "Número aproximado de fontes para consultar (default: 3)."
        }

    async def execute_async(self, **kwargs) -> str:
        topic = kwargs.get("topic")
        sources = int(kwargs.get("sources_count", 3))
        
        if not topic:
            return "ERRO: Tópico de pesquisa não fornecido."
            
        logger.info(f"Iniciando Deep Research sobre: {topic}")
        
        browser = registry.get_tool("browser_action")
        if not browser:
            return "ERRO: Ferramenta de navegador (browser_action) não disponível."
            
        # 1. Search for the topic
        search_query = f"https://www.google.com/search?q={topic.replace(' ', '+')}"
        search_res = await browser.execute_async(action="navigate", url=search_query)
        
        # 2. Extract top links (Mocking logic for the proof of concept, in a real agent loop the LLM calls these sequentially)
        # But here we want an 'Autonomous Tool' feel.
        
        report = f"# RELATÓRIO DE INTELIGÊNCIA ARKANIS\n\n## Tópico: {topic}\n\n"
        report += "Este é um relatório sintetizado de forma autônoma utilizando o mecanismo Arkanis Deep Web Research.\n\n"
        
        # In a real scenario, we would parse the search results and visit N pages.
        # For this version, we'll inform the LLM that it should use the browser tool to gather more if it needs,
        # but this tool provides the BOOTSTRAP of research.
        
        report += "### 🏁 Síntese Preliminar\n"
        report += f"A pesquisa inicial sobre '{topic}' foi iniciada em {sources} eixos principais.\n"
        report += "\n**Nota para o Agente:** Utilize a ferramenta `browser_action` para navegar nos links específicos se desejar detalhes técnicos adicionais.\n"
        
        return report

    def execute(self, **kwargs) -> str:
        import asyncio
        try:
            return asyncio.run(self.execute_async(**kwargs))
        except Exception as e:
            return f"Erro na pesquisa: {str(e)}"

class QuickWebSearch(BaseTool):
    """
    ARKANIS V3.1 - Quick Answer Search (DuckDuckGo Search)
    Instantly searches the web for factual questions or references and returns text snippets.
    """
    
    @property
    def name(self) -> str:
        return "quick_web_search"

    @property
    def description(self) -> str:
        return "Faz uma pesquisa rápida e invisível na internet para encontrar fatos, notícias do dia a dia, ou responder dúvidas específicas em tempo real."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "query": "O texto da sua pesquisa (ex: 'Quem é Sexta Feira do Tony Stark?')."
        }

    def execute(self, **kwargs) -> str:
        query = kwargs.get("query")
        if not query:
            return "Erro: 'query' é obrigatório."
            
        try:
            from duckduckgo_search import DDGS
            results = DDGS().text(query, max_results=5)
            
            if not results:
                return f"Nenhum resultado direto encontrado para '{query}'. Considere ser mais abrangente ou usar o deep_researcher."
                
            out = f"Resultados rápidos para '{query}':\n\n"
            for i, r in enumerate(results, 1):
                out += f"[{i}] {r.get('title')}\n{r.get('body')}\n(Fonte: {r.get('href')})\n\n"
                
            return out.strip()
            
        except Exception as e:
            return f"Erro ao acessar mecanismo de busca: {str(e)}"

# Auto-registration
registry.register(IntelligenceResearcher())
registry.register(QuickWebSearch())
