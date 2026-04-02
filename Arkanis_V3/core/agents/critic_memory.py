import os
import json
import threading
import time
from typing import List, Dict, Any, Optional

CRITIC_MEM_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data", "critic_lessons.json")

class CriticMemory:
    """
    EVOLUTIONARY MEMORY FOR THE CRITIC AGENT.
    Stores and retrieves lessons learned from past audits to provide proactive warnings.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.lessons: List[Dict[str, Any]] = []
        self.max_lessons = 50
        self._load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(CRITIC_MEM_FILE), exist_ok=True)

    def _load(self):
        with self._lock:
            if os.path.exists(CRITIC_MEM_FILE):
                try:
                    with open(CRITIC_MEM_FILE, "r", encoding="utf-8") as f:
                        self.lessons = json.load(f)
                except Exception as e:
                    print(f"[CriticMemory] Failed to load lessons: {e}")

    def _save(self):
        self._ensure_dir()
        with self._lock:
            try:
                with open(CRITIC_MEM_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.lessons, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"[CriticMemory] Failed to save lessons: {e}")

    def record_lesson(self, goal: str, issues: List[str]):
        """Record recurring issues found for a specific goal pattern."""
        if not issues:
            return

        # Simplified pattern: goal keywords
        goal_keywords = set(goal.lower().split())
        
        with self._lock:
            found = False
            for item in self.lessons:
                item_keywords = set(item["goal_pattern"].lower().split())
                # If 70% match or similar, consider it the same pattern
                if len(goal_keywords.intersection(item_keywords)) / max(len(goal_keywords), 1) > 0.7:
                    # Update lessons (no duplicates)
                    for issue in issues:
                        if issue not in item["lessons"]:
                            item["lessons"].append(issue)
                    item["fail_count"] += 1
                    item["last_seen"] = time.ctime()
                    found = True
                    break
            
            if not found:
                self.lessons.append({
                    "goal_pattern": goal,
                    "lessons": issues,
                    "fail_count": 1,
                    "last_seen": time.ctime()
                })
            
            # Enforce limit
            if len(self.lessons) > self.max_lessons:
                self.lessons.pop(0)

        self._save()

    def query_lessons(self, goal: str) -> str:
        """Find lessons related to the current goal."""
        goal_keywords = set(goal.lower().split())
        relevant_lessons = []

        with self._lock:
            for item in self.lessons:
                item_keywords = set(item["goal_pattern"].lower().split())
                if len(goal_keywords.intersection(item_keywords)) / max(len(goal_keywords), 1) > 0.5:
                    relevant_lessons.extend(item["lessons"])
        
        if not relevant_lessons:
            return ""
            
        # Deduplicate and format
        unique_lessons = list(set(relevant_lessons))[:5] # Top 5 lessons
        return "\n".join([f"- LIÇÃO: {l}" for l in unique_lessons])
