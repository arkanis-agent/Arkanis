from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
import os

class PlaywrightManager:
    """
    Singleton-like manager for Playwright session.
    Keeps context between tool calls during execution.
    """
    _playwright = None
    _browser = None
    _context = None
    _page = None

    @classmethod
    def get_page(cls):
        if not cls._playwright:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                raise RuntimeError("Playwright não instalado. Execute: pip install playwright && playwright install chromium")
            cls._playwright = sync_playwright().start()
            cls._browser = cls._playwright.chromium.launch(headless=True)
            cls._context = cls._browser.new_context(
                user_agent="ArkanisOS/V3.1 (Browser-RPA-Kernel)"
            )
            cls._page = cls._context.new_page()
        return cls._page

    @classmethod
    def close(cls):
        if cls._browser:
            cls._browser.close()
        if cls._playwright:
            cls._playwright.stop()
        cls._playwright = None
        cls._browser = None
        cls._context = None
        cls._page = None

class BrowserOpenTool(BaseTool):
    """Tool to open a specific URL in the headless browser."""
    @property
    def name(self) -> str: return "browser_open"
    @property
    def description(self) -> str: return "Opens a URL in the browser. Must be the first step for web automation."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"url": "The full URL to open (e.g., https://google.com)"}
    
    def execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        if not url: return "Error: Missing URL."
        try:
            page = PlaywrightManager.get_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            return f"Successfully opened {url}. Current title: {page.title()}"
        except Exception as e:
            return f"Error opening {url}: {str(e)}"

class BrowserClickTool(BaseTool):
    """Tool to click an element in the current page."""
    @property
    def name(self) -> str: return "browser_click"
    @property
    def description(self) -> str: return "Clicks an element on the current page using a CSS or XPath selector."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"selector": "CSS or XPath selector of the element to click (e.g., 'button#submit', 'text=Enviar')"}
    
    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector")
        if not selector: return "Error: Missing selector."
        try:
            page = PlaywrightManager.get_page()
            page.wait_for_selector(selector, timeout=5000)
            page.click(selector)
            return f"Successfully clicked element: {selector}"
        except Exception as e:
            return f"Error clicking {selector}: {str(e)}"

class BrowserFillTool(BaseTool):
    """Tool to fill an input field."""
    @property
    def name(self) -> str: return "browser_fill"
    @property
    def description(self) -> str: return "Fills an input field with the specified value."
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "selector": "The selector of the input field.",
            "value": "The text to fill in the field."
        }
    
    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector")
        value = kwargs.get("value")
        if not selector or value is None: return "Error: Missing selector or value."
        try:
            page = PlaywrightManager.get_page()
            page.wait_for_selector(selector, timeout=5000)
            page.fill(selector, str(value))
            return f"Successfully filled {selector} with value."
        except Exception as e:
            return f"Error filling {selector}: {str(e)}"

class BrowserSubmitTool(BaseTool):
    """Tool to submit a form or press Enter."""
    @property
    def name(self) -> str: return "browser_submit"
    @property
    def description(self) -> str: return "Submits a form by pressing Enter on the specified element."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"selector": "The element to press Enter on (usually an input field)."}
    
    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector")
        if not selector: return "Error: Missing selector."
        try:
            page = PlaywrightManager.get_page()
            page.press(selector, "Enter")
            return f"Successfully submitted via {selector}."
        except Exception as e:
            return f"Error submitting {selector}: {str(e)}"

class BrowserExtractTool(BaseTool):
    """Tool to extract text from an element or the entire page."""
    @property
    def name(self) -> str: return "browser_extract"
    @property
    def description(self) -> str: return "Extracts text from a specific element or the entire page if no selector is provided."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"selector": "Optional CSS/XPath selector. If omitted, returns all visible text from the body."}
    
    def execute(self, **kwargs) -> str:
        selector = kwargs.get("selector", "body")
        try:
            page = PlaywrightManager.get_page()
            page.wait_for_selector(selector, timeout=5000)
            text = page.inner_text(selector)
            return text[:5000] # Limit output to 5000 chars
        except Exception as e:
            return f"Error extracting from {selector}: {str(e)}"

class BrowserScreenshotTool(BaseTool):
    """Tool to take a screenshot of the current page."""
    @property
    def name(self) -> str: return "browser_screenshot"
    @property
    def description(self) -> str: return "Takes a screenshot of the current browser page."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"filename": "Optional name for the screenshot file (default: screenshot.png)."}
    
    def execute(self, **kwargs) -> str:
        filename = kwargs.get("filename", "screenshot.png")
        if not filename.endswith(".png"): filename += ".png"
        
        # Ensure directory exists
        os.makedirs("screenshots", exist_ok=True)
        path = os.path.join("screenshots", filename)
        
        try:
            page = PlaywrightManager.get_page()
            page.screenshot(path=path)
            return f"Screenshot saved successfully at: {path}"
        except Exception as e:
            return f"Error taking screenshot: {str(e)}"

# Auto-registration
from tools.registry import registry
registry.register(BrowserOpenTool())
registry.register(BrowserClickTool())
registry.register(BrowserFillTool())
registry.register(BrowserSubmitTool())
registry.register(BrowserExtractTool())
registry.register(BrowserScreenshotTool())
