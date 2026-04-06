import asyncio
import os
import uuid
from typing import Any, Dict, Optional
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time

class AutonomousBrowserTool(BaseTool):
    """
    ARKANIS V3.1 - Web Operative Tool
    Autonomous browser interaction using Playwright.
    Powerful for interacting with SPAs, dashboards, and complex web apps.
    """
    
    # Class variables for resource tracking
    _browser_pool = {}
    
    def __init__(self):
        super().__init__()
        self.screenshot_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "webui", 
            "screenshots"
        )
        os.makedirs(self.screenshot_dir, exist_ok=True)

    @property
    def name(self) -> str:
        return "autonomous_browser"

    @property
    def description(self) -> str:
        return "Full browser automation tool. Use this to navigate, click buttons, fill forms, and take screenshots of any website."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "url": "Target URL to navigate to.",
            "action": "Action to perform: 'screenshot', 'scrape', 'click', 'type'.",
            "selector": "Optional CSS selector for 'click' or 'type' actions.",
            "text": "Optional text for 'type' action.",
            "wait_ms": "Wait time in ms before the action (default 2000)."
        }

    def execute(self, **kwargs) -> str:
        try:
            return asyncio.run(self.execute_async(**kwargs))
        except Exception as e:
            logger.error(f"Autonomous Browser Sync Error: {str(e)}")
            return f"Error: {str(e)}"

    async def execute_async(self, **kwargs) -> str:
        url = kwargs.get("url")
        action = kwargs.get("action", "screenshot")
        selector = kwargs.get("selector")
        text = kwargs.get("text")
        wait_ms = int(kwargs.get("wait_ms", 2000))
        
        if not url:
            return "Error: Missing 'url' argument."

        if not str(url).startswith("http"):
            url = f"https://{url}"

        browser = None
        page = None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1280, "height": 800})
                
                # User-Agent identification
                await page.setUserAgent("Arkanis-Agent/3.1")
                
                # Navigation with proper timeout
                logger.info(f"Navigating to {url}...")
                await page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Smarter waiting - wait for page to be stable
                if wait_ms > 0:
                    await asyncio.sleep(wait_ms / 1000)
                
                # Specific Actions with better error handling
                if action == "click" and selector:
                    try:
                        await page.click(selector, timeout=20000)
                        await asyncio.sleep(1)
                    except Exception as e:
                        return f"Error clicking {selector}: {str(e)}"
                
                elif action == "type" and selector and text:
                    try:
                        await page.type(selector, text)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(2)
                    except Exception as e:
                        return f"Error typing in {selector}: {str(e)}"
                
                # Result Generation with screenshot timeout
                screenshot_filename = f"browser_{uuid.uuid4().hex[:8]}.png"
                screenshot_path = os.path.join(self.screenshot_dir, screenshot_filename)
                
                await page.screenshot(path=screenshot_path, full_page=True, timeout=30000)
                
                page_content = await page.content()
                soup = BeautifulSoup(page_content, "html.parser")
                
                # Remove scripts and styles
                for s in soup(["script", "style"]):
                    s.decompose()
                clean_text = soup.get_text(separator="\n", strip=True)
            
            await browser.close()
            report = [
                f"Result: Successfully performed '{action}' on {url}.",
                f"[SCREENSHOT_GENERATED: {screenshot_filename}]"
            ]
            
            if action == "scrape":
                report.append(f"SCRAPED_TEXT (Preview):\n{clean_text[:1000]}...")
            
            return "\n".join(report)

        except Exception as e:
            logger.error(f"Browser session error: {str(e)}")
            # Ensure cleanup in all failure scenarios
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            return f"Error during browser session: {str(e)}"

# Auto-registration
registry.register(AutonomousBrowserTool())