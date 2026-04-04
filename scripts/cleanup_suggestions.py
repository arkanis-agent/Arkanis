import os
import json
import re

def normalize(text):
    """Normalize text for better matching by removing whitespace and comments."""
    text = re.sub(r'#.*', '', text)
    return "".join(text.split()).strip()

def main():
    project_root = "/home/diego/Área de trabalho/Arkanis_V3.1"
    suggestions_file = os.path.join(project_root, "data", "suggestions.json")
    
    if not os.path.exists(suggestions_file):
        print(f"File not found: {suggestions_file}")
        return

    with open(suggestions_file, "r", encoding="utf-8") as f:
        suggestions = json.load(f)

    if not isinstance(suggestions, list):
        print("Invalid suggestions format.")
        return

    print(f"Auditing {len(suggestions)} suggestions...")
    cleaned_count = 0
    total_audited = 0

    for s in suggestions:
        if s.get("status") != "pending":
            continue
            
        total_audited += 1
        file_path = s.get("file_path")
        if not file_path:
            continue
            
        # Ensure path is absolute and within root
        if not os.path.isabs(file_path):
            abs_path = os.path.join(project_root, file_path)
        else:
            abs_path = file_path
            
        if not os.path.exists(abs_path):
            continue
            
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                current_content = f.read()
            
            proposed = s.get("proposed_code", "")
            if not proposed:
                continue
                
            # Heuristic 1: Exact snippet match (normalized)
            norm_proposed = normalize(proposed)
            norm_content = normalize(current_content)
            
            if norm_proposed in norm_content:
                s["status"] = "applied"
                cleaned_count += 1
                print(f" [✓] Marked as Applied: {s['title']} ({os.path.basename(abs_path)})")
            
            # Heuristic 2: Title based implementation check
            # (e.g. if title is "Enable Hot-Reload" and main.py has reload=True)
            elif "hot-reload" in s["title"].lower() and "reload=True" in current_content:
                s["status"] = "applied"
                cleaned_count += 1
                print(f" [✓] Marked as Applied (Logic Match): {s['title']}")
                
            elif "suggestionactionrequest" in s["title"].lower() and "SuggestionActionRequest" in current_content:
                s["status"] = "applied"
                cleaned_count += 1
                print(f" [✓] Marked as Applied (Logic Match): {s['title']}")

        except Exception as e:
            print(f" [!] Error auditing {file_path}: {e}")

    # Save results
    with open(suggestions_file, "w", encoding="utf-8") as f:
        json.dump(suggestions, f, indent=4)

    print(f"\nAudit complete!")
    print(f"Total Audited: {total_audited}")
    print(f"Already Implemented: {cleaned_count}")
    print(f"Remaining Pending: {total_audited - cleaned_count}")

if __name__ == "__main__":
    main()
