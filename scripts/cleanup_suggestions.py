import os
import json
import re
from pathlib import Path

def normalize(text):
    """Normalize text for better matching by removing whitespace, comments, and special characters."""
    if not text:
        return ""
    text = re.sub(r'#.*', '', text)
    text = re.sub(r'\W+', '', text)
    return text.lower().strip()

def main():
    project_root = Path(os.getenv("ARKANIS_ROOT", Path(__file__).parents[1]))
    suggestions_file = project_root / "data" / "suggestions.json"
    
    if not suggestions_file.exists():
        print(f"File not found: {suggestions_file}")
        return

    try:
        with open(suggestions_file, "r", encoding="utf-8") as f:
            suggestions = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading suggestions file: {e}")
        return

    if not isinstance(suggestions, list):
        print("Invalid suggestions format: Expected a list.")
        return

    print(f"Auditing {len(suggestions)} suggestions...")
    cleaned_count = 0
    total_audited = 0
    changes_made = False

    logic_matches = {
        "hot-reload": "reload=True",
        "suggestionactionrequest": "SuggestionActionRequest"
    }

    for s in suggestions:
        if s.get("status") != "pending":
            continue
            
        total_audited += 1
        file_path_str = s.get("file_path")
        if not file_path_str:
            continue
            
        abs_path = Path(file_path_str)
        if not abs_path.is_absolute():
            abs_path = project_root / file_path_str
            
        if not abs_path.exists():
            continue
            
        try:
            current_content = abs_path.read_text(encoding="utf-8")
            proposed = s.get("proposed_code", "")
            title = s.get("title", "").lower()

            is_applied = False
            reason = ""

            # Heuristic 1: Exact snippet match (normalized)
            if proposed:
                norm_proposed = normalize(proposed)
                norm_content = normalize(current_content)
                if norm_proposed and norm_proposed in norm_content:
                    is_applied = True
                    reason = "Snippet Match"
            
            # Heuristic 2: Dynamic Logic Match
            if not is_applied:
                for keyword, signature in logic_matches.items():
                    if keyword in title and signature in current_content:
                        is_applied = True
                        reason = f"Logic Match ({keyword})"
                        break

            if is_applied:
                s["status"] = "applied"
                cleaned_count += 1
                changes_made = True
                print(f" [✓] Marked as Applied: {s.get('title')} -> {reason} ({abs_path.name})")

        except Exception as e:
            print(f" [!] Error auditing {file_path_str}: {e}")

    if changes_made:
        with open(suggestions_file, "w", encoding="utf-8") as f:
            json.dump(suggestions, f, indent=4)
        print("\nChanges saved to suggestions.json.")
    else:
        print("\nNo changes detected. File not updated.")

    print(f"Audit complete!")
    print(f"Total Audited: {total_audited}")
    print(f"Already Implemented: {cleaned_count}")
    print(f"Remaining Pending: {total_audited - cleaned_count}")

if __name__ == "__main__":
    main()