import requests
import json
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry

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
            # Quick check to a reliable endpoint
            requests.get("https://1.1.1.1", timeout=3)
            return "true"
        except (requests.ConnectionError, requests.Timeout):
            return "false"

class FetchUrlTool(BaseTool):
    """A tool to fetch the text content of a URL."""
    @property
    def name(self) -> str: return "fetch_url"
    @property
    def description(self) -> str: 
        return "Fetch the raw text content of a given URL. Useful for reading web pages."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"url": "The full URL to fetch content from (e.g., https://example.com)"}
    def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        if not url: return "Error: Missing URL."
        
        try:
            # Set a 5s timeout and 2000 chars limit as requested
            headers = {'User-Agent': 'ArkanisOS/V3.1 (AI-Agent-Kernel)'}
            response = requests.get(url, timeout=5, headers=headers, verify=False)
            response.raise_for_status()
            
            # Parse HTML to extract visible text
            from html.parser import HTMLParser
            
            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                    self.hide_content = False
                    self.ignore_tags = {'script', 'style', 'head', 'meta', 'link'}
                
                def handle_starttag(self, tag, attrs):
                    if tag in self.ignore_tags:
                        self.hide_content = True
                
                def handle_endtag(self, tag):
                    if tag in self.ignore_tags:
                        self.hide_content = False
                
                def handle_data(self, data):
                    if not self.hide_content:
                        clean = data.strip()
                        if clean:
                            self.text.append(clean)
                
                def get_text(self):
                    return " ".join(self.text)

            content = response.text
            
            # If it looks like HTML, extract the text
            if "text/html" in response.headers.get("Content-Type", "").lower():
                try:
                    parser = HTMLTextExtractor()
                    parser.feed(content)
                    content = parser.get_text()
                except:
                    pass # Fallback to raw text if parsing fails
            
            limit = 2000
            if len(content) > limit:
                return content[:limit] + "\n\n... (Content truncated for performance)"
            return content
        except requests.Timeout:
            return "Error: Request timed out after 5 seconds."
        except requests.exceptions.HTTPError as e:
            return f"Error: HTTP {response.status_code} - {str(e)}"
        except Exception as e:
            return f"Error: Failed to fetch URL -> {str(e)}"

class HttpGetTool(BaseTool):
    """A tool to perform a simple HTTP GET request and return the JSON/text."""
    @property
    def name(self) -> str: return "http_get"
    @property
    def description(self) -> str: return "Perform a GET request to a URL. Returns the response text or JSON."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"url": "The full URL to request (e.g., https://api.ipify.org?format=json)"}
    
    def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        if not url: return "Error: Missing URL."
        try:
            response = requests.get(url, timeout=10, verify=False)
            return response.text
        except Exception as e:
            return f"Error: HTTP GET failed -> {str(e)}"

class HttpPostTool(BaseTool):
    """A tool to perform an HTTP POST request with a JSON payload."""
    @property
    def name(self) -> str: return "http_post"
    @property
    def description(self) -> str: return "Perform a POST request to a URL with a JSON payload."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "url": "The target URL.",
            "payload": "A dictionary or JSON string to send as payload."
        }
    
    def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        payload = kwargs.get("payload", {})
        if not url: return "Error: Missing URL."
        
        # Ensure payload is a dict if it's a string
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except: pass

        try:
            response = requests.post(url, json=payload, timeout=10, verify=False)
            return response.text
        except Exception as e:
            return f"Error: HTTP POST failed -> {str(e)}"

class WebSearchTool(BaseTool):
    """A tool to search the web for information using DuckDuckGo."""
    @property
    def name(self) -> str: return "web_search"
    @property
    def description(self) -> str: return "Search the internet for news, information, or current events. Use this BEFORE fetching specific URLs."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"query": "The search query (e.g., 'latest news on US economy')"}
    
    def execute(self, **kwargs) -> str:
        query = kwargs.get("query")
        if not query: return "Error: Missing search query."
        
        try:
            # DuckDuckGo Lite version for easy scraping without JS
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            headers = {'User-Agent': 'ArkanisOS/V3.1 (Web-Intelligence-Kernel)'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            from html.parser import HTMLParser
            
            class DDGParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.results = []
                    self.current_title = None
                    self.current_link = None
                    self.in_result = False
                    self.in_title = False
                    self.in_snippet = False
                    
                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    if tag == "div" and "result" in attrs_dict.get("class", ""):
                        self.in_result = True
                    if self.in_result:
                        if tag == "a" and "result__a" in attrs_dict.get("class", ""):
                            self.in_title = True
                            self.current_link = attrs_dict.get("href")
                        if tag == "a" and "result__snippet" in attrs_dict.get("class", ""):
                            self.in_snippet = True
                            
                def handle_endtag(self, tag):
                    if tag == "div" and self.in_result:
                        if self.current_title and self.current_link:
                            self.results.append(f"- {self.current_title}\n  URL: {self.current_link}")
                        self.current_title = None
                        self.current_link = None
                        self.in_result = False
                    if tag == "a":
                        self.in_title = False
                        self.in_snippet = False
                        
                def handle_data(self, data):
                    if self.in_title:
                        self.current_title = data.strip()
            
            parser = DDGParser()
            parser.feed(response.text)
            
            if not parser.results:
                return "No real-time results found. Try a different query."
                
            return "\n".join(parser.results[:5]) # Top 5 results
        except Exception as e:
            return f"Search Error: {str(e)}. Use direct fetch if you have a URL."

# Auto-registration
registry.register(CheckInternetTool())
registry.register(FetchUrlTool())
registry.register(HttpGetTool())
registry.register(HttpPostTool())
registry.register(WebSearchTool())
