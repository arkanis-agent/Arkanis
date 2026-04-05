import os
import json
import re
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUGGESTIONS_FILE = PROJECT_ROOT / "data" / "suggestions.json"

def normalize(text: str) -> str:
    """Normalize text by removing comments and whitespace for reliable substring matching."""
    text = re.sub(r'#.*$', '', text, flags=re.MULTILINE)
    return "".join(text.split())

def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Ensure target path is strictly within the base directory to prevent path traversal."""
    base = base_dir.resolve()
    target = target_path.resolve()
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False

def main():
    if not SUGGESTIONS_FILE.exists():
        print(f"File not found: {SUGGESTIONS_FILE}")
        return

    try:
        with open(SUGGESTIONS_FILE, "r", encoding="utf-8") as f:
            suggestions = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {SUGGESTIONS_FILE}: {e}")
        return

    if not isinstance(suggestions, list):
        print("Invalid suggestions format.")
        return

    print(f"Auditing {len(suggestions)} suggestions...")
    cleaned_count = 0
    total_audited = 0
    file_cache = {}

    for s in suggestions:
        if s.get("status") != "pending":
            continue

        total_audited += 1
        file_path_str = s.get("file_path")
        if not file_path_str:
            continue

        target_path = Path(file_path_str)
        if not target_path.is_absolute():
            target_path = PROJECT_ROOT / target_path

        if not is_safe_path(PROJECT_ROOT, target_path):
            print(f" [!] Skipped (Path Traversal Risk): {file_path_str}")
            continue

        if not target_path.exists():
            continue

        target_resolved = str(target_path.resolve())
        if target_resolved not in file_cache:
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    file_cache[target_resolved] = f.read()
            except Exception as e:
                print(f" [!] Error reading {target_path}: {e}")
                continue

        current_content = file_cache[target_resolved]
        proposed = s.get("proposed_code", "")
        if not proposed:
            continue

        norm_proposed = normalize(proposed)
        norm_content = normalize(current_content)

        if norm_proposed in norm_content:
            s["status"] = "applied"
            cleaned_count += 1
            print(f" [✓] Marked as Applied: {s['title']} ({target_path.name})")
            continue

        title_lower = s["title"].lower()
        if "hot-reload" in title_lower and "reload=True" in current_content:
            s["status"] = "applied"
            cleaned_count += 1
            print(f" [✓] Marked as Applied (Logic Match): {s['title']}")
        elif "suggestionactionrequest" in title_lower and "SuggestionActionRequest" in current_content:
            s["status"] = "applied"
            cleaned_count += 1
            print(f" [✓] Marked as Applied (Logic Match): {s['title']}")

    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=SUGGESTIONS_FILE.parent, encoding="utf-8", suffix=".tmp") as tmp_f:
            json.dump(suggestions, tmp_f, indent=4, ensure_ascii=False)
            tmp_path = Path(tmp_f.name)
        tmp_path.replace(SUGGESTIONS_FILE)
        print("\nAudit complete!")
        print(f"Total Audited: {total_audited}")
        print(f"Already Implemented: {cleaned_count}")
        print(f"Remaining Pending: {total_audited - cleaned_count}")
    except Exception as e:
        print(f" [!] Failed to save suggestions: {e}")

if __name__ == "__main__":
    main()