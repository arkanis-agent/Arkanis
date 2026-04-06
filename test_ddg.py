import sys
import os

# Ensure we can import from venv
venv_path = os.path.join(os.getcwd(), ".venv", "lib", "python3.12", "site-packages")
if venv_path not in sys.path:
    sys.path.append(venv_path)

try:
    from duckduckgo_search import DDGS
    print("Import successful")
    query = "quando será lançado a parte dois do filme velozes e furiosos 10"
    with DDGS() as ddgs:
        results = [r for r in ddgs.text(query, region='wt-wt', safesearch='off', max_results=3)]
        print(f"Results found: {len(results)}")
        for r in results:
            print(f"- {r.get('title')}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
