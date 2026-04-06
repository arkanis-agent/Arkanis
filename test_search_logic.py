import sys
import os
import asyncio

# Ensure we can import from project root and venv
V3_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(V3_DIR)
venv_path = os.path.join(V3_DIR, ".venv", "lib", "python3.12", "site-packages")
if venv_path not in sys.path:
    sys.path.append(venv_path)

from tools.research_tools import QuickWebSearch, IntelligenceResearcher
from tools.registry import registry

# Mock/Setup registry
registry.register(IntelligenceResearcher())
search_tool = QuickWebSearch()

async def test_search():
    query = "quem é o diretor de velozes e furiosos 10"
    print(f"Testing search for: {query}")
    
    # We expect this to either work via DDGS or fallback to IntelligenceResearcher
    result = search_tool.execute(query=query)
    print("\n--- RESULT ---")
    print(result)
    print("--------------")

if __name__ == "__main__":
    asyncio.run(test_search())
