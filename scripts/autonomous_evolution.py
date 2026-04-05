import os
import json
import subprocess
import sys
import logging
import argparse
from datetime import datetime

# Arkanis Autonomous Evolution Engine
# Enables the system to apply internal improvements and self-correct.

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUGGESTIONS_FILE = os.path.join(PROJECT_ROOT, "data", "suggestions.json")
VERIFY_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "verify_intelligence.py")
LOG_FILE = os.path.join(PROJECT_ROOT, "logs", "evolution.log")

# Setup logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Evolution")

def run_verify():
    """Runs the verify_intelligence.py script and returns True if it passes."""
    try:
        result = subprocess.run([sys.executable, VERIFY_SCRIPT], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def apply_code(file_path, code):
    """Applies the proposed code to the target file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        return True
    except Exception as e:
        logger.error(f"Failed to write to {file_path}: {e}")
        return False

def rollback(file_path):
    """Uses git to rollback a specific file."""
    try:
        subprocess.run(["git", "checkout", "--", file_path], cwd=PROJECT_ROOT, check=True)
        logger.warning(f"Rollback successful for {file_path}")
        return True
    except Exception as e:
        logger.error(f"Rollback FAILED for {file_path}: {e}")
        return False

def commit_change(title):
    """Commits the change to git after a successful application."""
    try:
        subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"Auto-evolution: {title}"], cwd=PROJECT_ROOT, check=True)
        logger.info(f"Committed: {title}")
        return True
    except Exception as e:
        logger.error(f"Commit failed: {e}")
        return False

# Add project root to sys.path for internal imports
sys.path.append(PROJECT_ROOT)

def smart_merge(file_path, proposed_code):
    """
    Intelligently merges the proposed code into the existing file.
    If the code is a snippet, uses the LLM to perform the merge.
    """
    if not os.path.exists(file_path):
        return proposed_code

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            current_content = f.read()

        # Detection logic:
        # 1. Look for comments indicating partial code
        # 2. Significant size difference
        is_snippet = any(x in proposed_code for x in ["# Rest of", "# ...", "Remaining", "code remains"])
        if not is_snippet and 0.8 < (len(proposed_code) / (len(current_content) + 1)) < 1.2:
            return proposed_code

        logger.info(f"Snippet detected for {os.path.basename(file_path)}. Initiating Smart-Merge...")
        
        from core.llm_router import router
        
        system_prompt = "You are the Arkanis Code Merger. Your task is to accurately merge a requested improvement (snippet) into existing file content."
        user_prompt = f"""
FILE: {file_path}

CURRENT CONTENT:
```python
{current_content}
```

PROPOSED IMPROVEMENT (SNIPPET):
```python
{proposed_code}
```

TASK:
Merge the improvement into the current content. 
- DO NOT remove existing functionality unless explicitly replaced by the snippet.
- Maintain imports and structure.
- Return ONLY the full, final source code for the file.
- No markdown formatting, just the raw code.
"""
        merged_code = router.generate(system_prompt, user_prompt)
        
        if not merged_code or len(merged_code) < 10 or "Error" in merged_code:
            logger.warning("Smart-Merge failed or returned invalid result. Falling back to original suggestion.")
            return proposed_code
            
        # Clean up accidental markdown backticks
        if merged_code.startswith("```"):
            import re
            merged_code = re.sub(r"```python\n?|```", "", merged_code).strip()
            
        return merged_code.strip()
    except Exception as e:
        logger.error(f"Error during Smart-Merge: {e}")
        return proposed_code

def main():
    parser = argparse.ArgumentParser(description="Arkanis Autonomous Evolution Engine")
    parser.add_argument("--limit", type=int, default=1, help="Maximum number of suggestions to apply")
    parser.add_argument("--dry-run", action="store_true", help="Simulate changes without writing to disk")
    parser.add_argument("--force-merge", action="store_true", help="Force LLM merge for all files")
    args = parser.parse_args()

    if not os.path.exists(SUGGESTIONS_FILE):
        logger.error(f"Suggestions file not found: {SUGGESTIONS_FILE}")
        return

    try:
        with open(SUGGESTIONS_FILE, "r", encoding="utf-8") as f:
            suggestions = json.load(f)
    except Exception as e:
        logger.error(f"Failed to parse suggestions.json: {e}")
        return

    pending = [s for s in suggestions if s.get("status") == "pending" and s.get("file_path") is not None]
    if not pending:
        logger.info("No pending actionable suggestions found. Arkanis is optimized.")
        return

    count = min(len(pending), args.limit)
    logger.info(f"Found {len(pending)} pending actionable suggestions. Processing top {count}...")

    applied_count = 0
    for i in range(count):
        sug = pending[i]
        title = sug.get("title", "Untitled Suggestion")
        file_path = sug.get("file_path")
        
        # Normalize path to project root (handles Case-Sensitivity issues in the base path)
        if "Arkanis_V3.1" in file_path:
            rel_path = file_path.split("Arkanis_V3.1")[-1].lstrip("/")
            file_path = os.path.join(PROJECT_ROOT, rel_path)
            
        proposed_code = sug.get("proposed_code")
        sug_id = sug.get("id")

        if args.dry_run:
            logger.info(f"[DRY-RUN] Would apply: [{sug_id}] {title} to {file_path}")
            continue

        logger.info(f"Step {i+1}/{count}: Applying [{sug_id}] {title}")
        
        # 1. Smart-Merge
        final_code = smart_merge(file_path, proposed_code) if not args.force_merge else smart_merge(file_path, proposed_code)
        
        # 2. Apply code
        if apply_code(file_path, final_code):
            # 3. Verify
            success, output = run_verify()
            if success:
                logger.info(f"SUCCESS: System stable. Output: {output.strip()}")
                sug["status"] = "applied"
                sug["applied_at"] = datetime.utcnow().isoformat() + "Z"
                commit_change(title)
                applied_count += 1
            else:
                logger.error(f"FAILURE: Verification failed. Output: {output.strip()}")
                rollback(file_path)
                sug["status"] = "failed"
                sug["error"] = output.strip()
        else:
            sug["status"] = "error"
            sug["error"] = "Write access denied"

    if not args.dry_run:
        # Save updated status
        try:
            with open(SUGGESTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(suggestions, f, indent=4, ensure_ascii=False)
            logger.info(f"Evolution cycle complete. Applied {applied_count} changes.")
        except Exception as e:
            logger.error(f"Failed to save suggestions.json: {e}")

if __name__ == "__main__":
    main()
