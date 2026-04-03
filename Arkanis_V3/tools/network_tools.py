import requests
import json
import re
import time
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry

# Desabilitar warnings de SSL (ambiente local)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Headers realistas para evitar bloqueios
REALISTIC_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}


class CheckInternetTool(BaseTool):
    """A tool to check for internet connectivity."""
    @property
    def name(self) -> str: return "check_internet"
    @property
    def description(self) -> str: return "Verifies if there is an active internet connection."
    @property
    def arguments(self) -> Dict[str, str]: return {}

    def execute(self, **kwargs) -> str:
        try:
            requests.get("https://1.1.1.1", timeout=3)
            return "true"
        except (requests.ConnectionError, requests.Timeout):
            return "false"


class FetchUrlTool(BaseTool):
    """Fetches the text content of a URL with realistic browser headers."""
    @property
    def name(self) -> str: return "fetch_url"
    @property
    def description(self) -> str:
        return (
            "Fetch the text content of a URL. Works with most websites. "
            "Use browser_open for JavaScript-heavy or login-protected pages."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "url": "The full URL to fetch (e.g., https://example.com)",
            "max_chars": "Optional. Max characters to return (default: 3000)"
        }

    def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        max_chars = int(kwargs.get("max_chars", 3000))
        if not url:
            return "Error: Missing URL."
        try:
            response = requests.get(
                url, timeout=10, headers=REALISTIC_HEADERS,
                verify=False, allow_redirects=True
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()

            if "application/json" in content_type:
                return response.text[:max_chars]

            # HTML → texto visível
            from html.parser import HTMLParser

            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.hide = False
                    self.ignore = {'script', 'style', 'head', 'meta', 'link', 'noscript'}

                def handle_starttag(self, tag, attrs):
                    if tag in self.ignore:
                        self.hide = True

                def handle_endtag(self, tag):
                    if tag in self.ignore:
                        self.hide = False

                def handle_data(self, data):
                    if not self.hide:
                        clean = data.strip()
                        if clean:
                            self.text.append(clean)

                def get_text(self):
                    return " ".join(self.text)

            parser = HTMLTextExtractor()
            parser.feed(response.text)
            content = parser.get_text()

            if len(content) > max_chars:
                return content[:max_chars] + "\n\n... (truncado)"
            return content if content else response.text[:max_chars]

        except requests.Timeout:
            return "Error: Timeout ao acessar a URL (10s)."
        except requests.exceptions.HTTPError as e:
            return f"Error: HTTP {e.response.status_code} — {str(e)}"
        except Exception as e:
            return f"Error: Falha ao buscar URL → {str(e)}"


class HttpGetTool(BaseTool):
    """Performs a GET request and returns the raw response."""
    @property
    def name(self) -> str: return "http_get"
    @property
    def description(self) -> str:
        return "Perform a GET request to a URL. Best for REST APIs returning JSON."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "url": "The full URL (e.g., https://api.ipify.org?format=json)",
            "headers": "Optional JSON string with extra headers"
        }

    def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        extra_headers = kwargs.get("headers", "{}")
        if not url:
            return "Error: Missing URL."
        try:
            if isinstance(extra_headers, str):
                extra_headers = json.loads(extra_headers)
            merged = {**REALISTIC_HEADERS, **extra_headers}
            response = requests.get(url, timeout=15, headers=merged, verify=False)
            return response.text
        except Exception as e:
            return f"Error: HTTP GET failed → {str(e)}"


class HttpPostTool(BaseTool):
    """Performs an HTTP POST request with a JSON payload."""
    @property
    def name(self) -> str: return "http_post"
    @property
    def description(self) -> str:
        return "Perform a POST request to a URL with a JSON payload."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "url": "The target URL.",
            "payload": "A dictionary or JSON string to send as body."
        }

    def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        payload = kwargs.get("payload", {})
        if not url:
            return "Error: Missing URL."
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                pass
        try:
            response = requests.post(url, json=payload, timeout=15,
                                     headers=REALISTIC_HEADERS, verify=False)
            return response.text
        except Exception as e:
            return f"Error: HTTP POST failed → {str(e)}"


class WebSearchTool(BaseTool):
    """
    Searches the web with automatic fallback across multiple backends.
    Primary: DuckDuckGo JSON API → Fallback: DDG HTML Lite → Fallback: Bing.
    """
    @property
    def name(self) -> str: return "web_search"
    @property
    def description(self) -> str:
        return (
            "Search the internet for news, information, prices, or current events. "
            "Uses multiple backends with automatic fallback. Always works."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {"query": "The search query (e.g., 'preço do bitcoin hoje em reais')"}

    def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "").strip()
        if not query:
            return "Error: Missing search query."

        # --- Backend 1: DuckDuckGo JSON API (instant, no bot blocking) ---
        try:
            result = self._search_ddg_json(query)
            if result:
                return result
        except Exception as e:
            print(f"[WebSearch] DDG JSON falhou: {e}")

        # --- Backend 2: DuckDuckGo HTML Lite ---
        try:
            result = self._search_ddg_html(query)
            if result:
                return result
        except Exception as e:
            print(f"[WebSearch] DDG HTML falhou: {e}")

        # --- Backend 3: Bing ---
        try:
            result = self._search_bing(query)
            if result:
                return result
        except Exception as e:
            print(f"[WebSearch] Bing falhou: {e}")

        return (
            "SISTEMA: Nenhum resultado real ou atualizado foi encontrado para esta busca na internet. "
            "Aviso: Não utilize dados de treinamento obsoletos para responder. "
            "Se o usuário perguntou sobre fatos recentes, informe que a busca não retornou dados."
        )

    def _search_ddg_json(self, query: str) -> str:
        """DuckDuckGo Instant Answer API — rápida e confiável."""
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
            "no_redirect": "1",
        }
        resp = requests.get(url, params=params, timeout=8,
                            headers=REALISTIC_HEADERS, verify=False)
        resp.raise_for_status()
        data = resp.json()

        results = []

        # Resposta direta (Abstract)
        abstract = data.get("AbstractText", "").strip()
        if abstract:
            source = data.get("AbstractSource", "")
            results.append(f"📖 **{source}**: {abstract}")

        # Resposta direta (Answer)
        answer = data.get("Answer", "").strip()
        if answer:
            results.append(f"✅ **Resposta Direta**: {answer}")

        # Tópicos relacionados
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict):
                text = topic.get("Text", "").strip()
                link = topic.get("FirstURL", "")
                if text:
                    results.append(f"- {text}\n  🔗 {link}")

        if results:
            return "\n".join(results)
        return ""

    def _search_ddg_html(self, query: str) -> str:
        """DuckDuckGo HTML Lite — fallback de scraping."""
        from html.parser import HTMLParser
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=REALISTIC_HEADERS, timeout=10, verify=False)
        resp.raise_for_status()

        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self.current_title = None
                self.current_link = None
                self.current_snippet = None
                self.in_title = False
                self.in_snippet = False

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                css = attrs_dict.get("class", "")
                if tag == "a" and "result__a" in css:
                    self.in_title = True
                    href = attrs_dict.get("href", "")
                    # DDG redireciona via //duckduckgo.com/l/?uddg=URL
                    match = re.search(r"uddg=(https?[^&]+)", href)
                    self.current_link = requests.utils.unquote(match.group(1)) if match else href
                elif tag == "a" and "result__snippet" in css:
                    self.in_snippet = True

            def handle_endtag(self, tag):
                if tag == "a":
                    if self.in_title and self.current_title:
                        pass  # aguarda snippet
                    self.in_title = False
                    if self.in_snippet:
                        if self.current_title and self.current_link:
                            snip = self.current_snippet or ""
                            self.results.append(
                                f"- **{self.current_title}**\n  {snip}\n  🔗 {self.current_link}"
                            )
                        self.current_title = None
                        self.current_link = None
                        self.current_snippet = None
                        self.in_snippet = False

            def handle_data(self, data):
                if self.in_title:
                    self.current_title = data.strip()
                elif self.in_snippet:
                    self.current_snippet = (self.current_snippet or "") + data.strip()

        parser = DDGParser()
        parser.feed(resp.text)

        if parser.results:
            return "\n".join(parser.results[:6])
        return ""

    def _search_bing(self, query: str) -> str:
        """Bing HTML — terceiro fallback."""
        from html.parser import HTMLParser
        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}&setlang=pt-BR"
        resp = requests.get(url, headers=REALISTIC_HEADERS, timeout=10, verify=False)
        resp.raise_for_status()

        class BingParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self.in_h2 = False
                self.in_li_b = False
                self.current_title = None
                self.current_link = None

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == "li" and "b_algo" in attrs_dict.get("class", ""):
                    self.in_li_b = True
                if self.in_li_b and tag == "h2":
                    self.in_h2 = True
                if self.in_li_b and self.in_h2 and tag == "a":
                    self.current_link = attrs_dict.get("href", "")

            def handle_endtag(self, tag):
                if tag == "h2":
                    self.in_h2 = False
                if tag == "li":
                    if self.current_title and self.current_link:
                        self.results.append(
                            f"- **{self.current_title}**\n  🔗 {self.current_link}"
                        )
                    self.current_title = None
                    self.current_link = None
                    self.in_li_b = False

            def handle_data(self, data):
                if self.in_h2:
                    self.current_title = (self.current_title or "") + data.strip()

        parser = BingParser()
        parser.feed(resp.text)

        if parser.results:
            return "🔍 **Bing** (fallback):\n" + "\n".join(parser.results[:5])
        return ""


# --- Auto-registration ---
registry.register(CheckInternetTool())
registry.register(FetchUrlTool())
registry.register(HttpGetTool())
registry.register(HttpPostTool())
registry.register(WebSearchTool())
