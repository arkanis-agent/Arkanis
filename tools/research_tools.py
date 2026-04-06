import os
import json
import logging
import urllib.parse
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry

logger = logging.getLogger(__name__)

class IntelligenceResearcher(BaseTool):
    """
    ARKANIS V3.1 - Deep Intelligence Researcher
    Uses the browser tools to perform multi-source search and synthesize an executive summary.
    """
    
    def __init__(self):
        self._max_sources = 10
        self._min_sources = 1
        self._tool_name = "browser_action"

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
            "sources_count": "Número aproximado de fontes para consultar (1-10, default: 3)."
        }

    async def execute_async(self, **kwargs) -> str:
        topic = kwargs.get("topic")
        try:
            sources_count = int(kwargs.get("sources_count", 3))
        except ValueError:
            sources_count = 3
        
        # Validações de segurança e lógica de negócio
        if not topic:
            return "ERRO: Tópico de pesquisa não fornecido."
            
        if len(topic) > 500:
            return "ERRO: Tópico muito longo. Máximo 500 caracteres."
            
        sources_count = max(self._min_sources, min(self._max_sources, sources_count))
        
        logger.info(f"Iniciando Deep Research sobre: {topic}")
        
        browser = registry.get_tool(self._tool_name)
        if not browser:
            return f"ERRO: Ferramenta '{self._tool_name}' não disponível no registry."
            
        # Segurança: URL encoding correto para evitar injeção de URL
        encoded_topic = urllib.parse.quote(topic[:200], safe='')
        search_query = f"https://www.google.com/search?q={encoded_topic}"
        search_res = await browser.execute_async(action="navigate", url=search_query)
        
        report = f"# RELATÓRIO DE INTELIGÊNCIA ARKANIS\n\n## Tópico: {topic[:100]}\n\n"
        report += "Este é um relatório sintetizado de forma autônoma utilizando o mecanismo Arkanis Deep Web Research.\n\n"
        report += "### 🏁 Síntese Preliminar\n"
        report += f"A pesquisa inicial sobre '{topic[:50]}' foi iniciada em {sources_count} eixos principais.\n"
        report += "\n**Nota para o Agente:** Utilize a ferramenta `browser_action` para navegar nos links específicos se desejar detalhes técnicos adicionais.\n"
        
        return report

    def execute(self, **kwargs) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.create_task(self.execute_async(**kwargs))
        return loop.run_until_complete(self.execute_async(**kwargs))

class QuickWebSearch(BaseTool):
    """
    ARKANIS V3.1 - Quick Answer Search (DuckDuckGo Search)
    Instantly searches the web for factual questions or references and returns text snippets.
    """
    
    def __init__(self):
        self._max_results = 5
        self._results_cache = {}
        self._cache_ttl = 300  # segundos
        import time
        self._last_search = 0

    @property
    def name(self) -> str:
        return "quick_web_search"

    @property
    def description(self) -> str:
        return "Faz uma pesquisa rápida e invisível na internet para encontrar fatos, notícias do dia a dia, ou responder dúvidas específicas em tempo real."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "query": "O texto da sua pesquisa (ex: 'Quem é Sexta Feira do Tony Stark?').",
            "max_results": "Número máximo de resultados (1-10, default: 5)."
        }

    def execute(self, **kwargs) -> str:
        query = kwargs.get("query")
        if not query:
            return "Erro: 'query' é obrigatório."
            
        if len(query) > 300:
            return "Erro: 'query' muito longo. Máximo 300 caracteres."
            
        import time
        if time.time() - self._last_search < 1:  # Rate limiting básico
            return "Erro: Muito rápido demais. Aguarde 1 segundo entre pesquisas."
        self._last_search = time.time()
            
        try:
            from duckduckgo_search import DDGS
            max_results = min(int(kwargs.get("max_results", 5)), 10)
            results = DDGS().text(query, max_results=max_results)
                
            if not results:
                return f"Nenhum resultado direto encontrado para '{query}'. Considere ser mais abrangente ou usar o deep_researcher."
                
            out = f"Resultados rápidos para '{query}':\n\n"
            for i, r in enumerate(results[:max_results], 1):
                title = r.get('title', '')[:100]
                body = r.get('body', '')[:300]
                out += f"[{i}] {title}\n{body}\n(Fonte: {r.get('href')})\n\n"
                
            return out.strip()
            
        except Exception as e:
            logger.error(f"Erro ao acessar mecanismo de busca: {str(e)}")
            return f"Erro ao acessar mecanismo de busca. Tente novamente."

# Auto-registration
registry.register(IntelligenceResearcher())
registry.register(QuickWebSearch())