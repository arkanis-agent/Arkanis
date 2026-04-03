import os
import time
from typing import Dict, Any, Optional
from tools.base_tool import BaseTool

# User-agent de um Chrome real (Linux) para evitar bloqueios anti-bot
REAL_CHROME_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class PlaywrightManager:
    """
    Singleton para sessão Playwright persistente entre chamadas de tool.
    Usa user-agent real de Chrome para evitar bloqueios.
    Suporta modo headful via ARKANIS_BROWSER_HEADFUL=true
    """
    _playwright = None
    _browser = None
    _context = None
    _page = None

    @classmethod
    def _ensure_installed(cls):
        """Auto-instala Chromium se não estiver disponível."""
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            raise RuntimeError(
                "Playwright não instalado. Execute: "
                "pip install playwright && playwright install chromium"
            )

    @classmethod
    def get_page(cls):
        if cls._page and not cls._is_page_closed():
            return cls._page

        cls._ensure_installed()
        from playwright.sync_api import sync_playwright

        try:
            # Auto-install Chromium se necessário
            import subprocess
            try:
                subprocess.run(
                    ["playwright", "install", "chromium", "--with-deps"],
                    capture_output=True, timeout=120
                )
            except Exception:
                pass  # Se falhar, tenta continuar mesmo assim

            headful = os.environ.get("ARKANIS_BROWSER_HEADFUL", "false").lower() == "true"
            cls._playwright = sync_playwright().start()
            cls._browser = cls._playwright.chromium.launch(
                headless=not headful,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ]
            )
            cls._context = cls._browser.new_context(
                user_agent=REAL_CHROME_UA,
                viewport={"width": 1366, "height": 768},
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                java_script_enabled=True,
                accept_downloads=True,
            )
            # Ocultar flag de webdriver automação
            cls._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            cls._page = cls._context.new_page()
        except Exception as e:
            raise RuntimeError(f"Falha ao iniciar navegador: {e}")

        return cls._page

    @classmethod
    def _is_page_closed(cls) -> bool:
        try:
            return cls._page.is_closed()
        except Exception:
            return True

    @classmethod
    def close(cls):
        try:
            if cls._browser:
                cls._browser.close()
            if cls._playwright:
                cls._playwright.stop()
        except Exception:
            pass
        finally:
            cls._playwright = None
            cls._browser = None
            cls._context = None
            cls._page = None


# ─────────────────────────────────────────────
#  TOOLS
# ─────────────────────────────────────────────

class BrowserOpenTool(BaseTool):
    """Abre uma URL no navegador headless com suporte a SPAs."""
    @property
    def name(self) -> str: return "browser_open"
    @property
    def description(self) -> str:
        return (
            "Opens a URL in a real Chrome browser. Use for JavaScript-heavy sites, "
            "login pages, forms, or anything that fetch_url can't handle. "
            "Always call this FIRST before other browser_ tools."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "url": "The full URL to open (e.g., https://google.com)",
            "wait": "Optional: 'load', 'domcontentloaded', or 'networkidle' (default: domcontentloaded)"
        }

    def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        wait_until = kwargs.get("wait", "domcontentloaded")
        if not url:
            return "Error: URL ausente."
        valid_waits = {"load", "domcontentloaded", "networkidle", "commit"}
        if wait_until not in valid_waits:
            wait_until = "domcontentloaded"
        try:
            page = PlaywrightManager.get_page()
            page.goto(url, wait_until=wait_until, timeout=30000)
            # Extra wait para SPAs carregarem conteúdo assíncrono
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            title = page.title()
            current_url = page.url
            return f"✅ Página aberta: '{title}'\n   URL final: {current_url}"
        except Exception as e:
            return f"Error ao abrir {url}: {str(e)}"


class BrowserClickTool(BaseTool):
    """Clica num elemento da página atual."""
    @property
    def name(self) -> str: return "browser_click"
    @property
    def description(self) -> str:
        return "Clicks an element on the current page using a CSS or text selector."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "selector": (
                "CSS selector, XPath, or text selector. "
                "Examples: 'button#submit', 'text=Enviar', '//button[@type=\"submit\"]'"
            )
        }

    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector")
        if not selector:
            return "Error: selector ausente."
        try:
            page = PlaywrightManager.get_page()
            page.wait_for_selector(selector, timeout=8000, state="visible")
            page.click(selector)
            time.sleep(0.5)
            return f"✅ Clicado: {selector}"
        except Exception as e:
            return f"Error ao clicar '{selector}': {str(e)}"


class BrowserFillTool(BaseTool):
    """Preenche um campo de input."""
    @property
    def name(self) -> str: return "browser_fill"
    @property
    def description(self) -> str:
        return "Fills an input field with text. Use for forms, search boxes, login fields."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "selector": "CSS/XPath selector of the input field.",
            "value": "The text to fill in."
        }

    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector")
        value = kwargs.get("value")
        if not selector or value is None:
            return "Error: selector ou value ausente."
        try:
            page = PlaywrightManager.get_page()
            page.wait_for_selector(selector, timeout=8000, state="visible")
            page.fill(selector, str(value))
            return f"✅ Campo '{selector}' preenchido."
        except Exception as e:
            return f"Error ao preencher '{selector}': {str(e)}"


class BrowserSubmitTool(BaseTool):
    """Submete um formulário pressionando Enter."""
    @property
    def name(self) -> str: return "browser_submit"
    @property
    def description(self) -> str:
        return "Submits a form by pressing Enter on the specified element."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"selector": "Selector of the field to press Enter on."}

    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector")
        if not selector:
            return "Error: selector ausente."
        try:
            page = PlaywrightManager.get_page()
            page.press(selector, "Enter")
            time.sleep(1)
            return f"✅ Formulário submetido via Enter em '{selector}'."
        except Exception as e:
            return f"Error ao submeter '{selector}': {str(e)}"


class BrowserExtractTool(BaseTool):
    """Extrai texto visível de um elemento ou da página toda."""
    @property
    def name(self) -> str: return "browser_extract"
    @property
    def description(self) -> str:
        return (
            "Extracts visible text from a page element. "
            "If no selector, returns all visible body text. "
            "Use after browser_open."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "selector": "Optional CSS/XPath. If omitted, reads all body text.",
            "max_chars": "Optional max characters to return (default: 5000)"
        }

    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector", "body")
        max_chars = int(kwargs.get("max_chars", 5000))
        try:
            page = PlaywrightManager.get_page()
            try:
                page.wait_for_selector(selector, timeout=5000)
            except Exception:
                pass  # Tenta mesmo sem o selector aparecer
            text = page.inner_text(selector)
            if len(text) > max_chars:
                return text[:max_chars] + "\n... (truncado)"
            return text
        except Exception as e:
            return f"Error ao extrair '{selector}': {str(e)}"


class BrowserGetHtmlTool(BaseTool):
    """Retorna o HTML bruto de um elemento ou da página toda."""
    @property
    def name(self) -> str: return "browser_get_html"
    @property
    def description(self) -> str:
        return "Returns the raw HTML of a page element or the entire page."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "selector": "Optional selector. If omitted, returns full page HTML.",
            "max_chars": "Optional max chars (default: 8000)"
        }

    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector", "html")
        max_chars = int(kwargs.get("max_chars", 8000))
        try:
            page = PlaywrightManager.get_page()
            html = page.inner_html(selector)
            if len(html) > max_chars:
                return html[:max_chars] + "\n... (truncado)"
            return html
        except Exception as e:
            return f"Error ao obter HTML '{selector}': {str(e)}"


class BrowserScreenshotTool(BaseTool):
    """Tira screenshot da página atual."""
    @property
    def name(self) -> str: return "browser_screenshot"
    @property
    def description(self) -> str:
        return "Takes a screenshot of the current browser page and saves to screenshots/."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"filename": "Optional filename (default: screenshot.png)"}

    def execute(self, **kwargs) -> str:
        filename = kwargs.get("filename", "screenshot.png")
        if not filename.endswith(".png"):
            filename += ".png"
        os.makedirs("screenshots", exist_ok=True)
        path = os.path.join("screenshots", filename)
        try:
            page = PlaywrightManager.get_page()
            page.screenshot(path=path, full_page=True)
            return f"✅ Screenshot salvo em: {path}"
        except Exception as e:
            return f"Error ao tirar screenshot: {str(e)}"


class BrowserWaitTool(BaseTool):
    """Aguarda um elemento aparecer na página."""
    @property
    def name(self) -> str: return "browser_wait"
    @property
    def description(self) -> str:
        return (
            "Waits for an element to appear on the page. "
            "Use after browser_click or browser_submit to wait for results."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "selector": "CSS/XPath selector to wait for.",
            "timeout": "Optional timeout in milliseconds (default: 10000)"
        }

    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector")
        timeout = int(kwargs.get("timeout", 10000))
        if not selector:
            return "Error: selector ausente."
        try:
            page = PlaywrightManager.get_page()
            page.wait_for_selector(selector, timeout=timeout, state="visible")
            return f"✅ Elemento '{selector}' apareceu na página."
        except Exception as e:
            return f"⚠️ Timeout aguardando '{selector}': {str(e)}"


class BrowserSelectTool(BaseTool):
    """Seleciona uma opção num elemento <select>."""
    @property
    def name(self) -> str: return "browser_select"
    @property
    def description(self) -> str:
        return "Selects an option in a <select> dropdown element."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "selector": "CSS selector of the <select> element.",
            "value": "The option value or visible label to select."
        }

    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector")
        value = kwargs.get("value")
        if not selector or value is None:
            return "Error: selector ou value ausente."
        try:
            page = PlaywrightManager.get_page()
            page.wait_for_selector(selector, timeout=5000)
            # Tenta por value, label, ou index
            try:
                page.select_option(selector, value=str(value))
            except Exception:
                page.select_option(selector, label=str(value))
            return f"✅ Opção '{value}' selecionada em '{selector}'."
        except Exception as e:
            return f"Error ao selecionar '{value}' em '{selector}': {str(e)}"


class BrowserGetUrlTool(BaseTool):
    """Retorna a URL atual da página no navegador."""
    @property
    def name(self) -> str: return "browser_get_url"
    @property
    def description(self) -> str:
        return "Returns the current URL of the browser page. Useful to track navigation."
    @property
    def arguments(self) -> Dict[str, str]:
        return {}

    def execute(self, **kwargs) -> str:
        try:
            page = PlaywrightManager.get_page()
            return f"URL atual: {page.url}"
        except Exception as e:
            return f"Error ao obter URL: {str(e)}"


class BrowserScrollTool(BaseTool):
    """Rola a página para o fundo para carregar conteúdo dinâmico."""
    @property
    def name(self) -> str: return "browser_scroll"
    @property
    def description(self) -> str:
        return (
            "Scrolls the page to load dynamic content (infinite scroll, lazy loading). "
            "Use before browser_extract on social media or news feeds."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "direction": "Optional: 'bottom' or 'top' (default: bottom)",
            "times": "Optional: how many times to scroll (default: 3)"
        }

    def execute(self, **kwargs) -> str:
        direction = kwargs.get("direction", "bottom")
        times = int(kwargs.get("times", 3))
        try:
            page = PlaywrightManager.get_page()
            for i in range(times):
                if direction == "top":
                    page.evaluate("window.scrollTo(0, 0)")
                else:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(0.8)
            return f"✅ Página rolada {times}x para {direction}."
        except Exception as e:
            return f"Error ao rolar página: {str(e)}"


# ─────────────────────────────────────────────
#  Auto-registration
# ─────────────────────────────────────────────
from tools.registry import registry

registry.register(BrowserOpenTool())
registry.register(BrowserClickTool())
registry.register(BrowserFillTool())
registry.register(BrowserSubmitTool())
registry.register(BrowserExtractTool())
registry.register(BrowserGetHtmlTool())
registry.register(BrowserScreenshotTool())
registry.register(BrowserWaitTool())
registry.register(BrowserSelectTool())
registry.register(BrowserGetUrlTool())
registry.register(BrowserScrollTool())
