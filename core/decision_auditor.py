import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("uvicorn")

class DecisionAuditor:
    """
    ARKANIS V3.1 - Autonomous Decision Auditor
    Tracks agent failures and successes to build a persistent 'Lessons Learned' database.
    This enables the system to self-correct and avoid repeating past technical mistakes.
    """
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.lessons_file = os.path.join(self.base_dir, "data", "critic_lessons.json")
        self.lessons = self._load_lessons()

    def _load_lessons(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.lessons_file):
            try:
                with open(self.lessons_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load lessons: {e}")
        return []

    def _save_lessons(self):
        try:
            with open(self.lessons_file, "w", encoding="utf-8") as f:
                json.dump(self.lessons, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save lessons: {e}")

    def record_lesson(self, goal: str, results: List[str]):
        """
        Analyzes execution results for errors and records them as lessons.
        """
        errors = [r for r in results if "[Error]" in str(r) or "falha" in str(r).lower() or "error" in str(r).lower()]
        if not errors:
            return

        # Simple pattern matching for the goal (grouping similar goals)
        goal_pattern = goal.strip()
        
        # Look for existing pattern
        found = False
        for item in self.lessons:
            if item["goal_pattern"].lower() == goal_pattern.lower():
                # Add new unique errors as lessons
                for err in errors:
                    clean_err = str(err).split(":", 1)[-1].strip() if ":" in str(err) else str(err)
                    if clean_err not in item["lessons"]:
                        item["lessons"].append(clean_err)
                item["fail_count"] = item.get("fail_count", 0) + 1
                item["last_seen"] = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
                found = True
                break
        
        if not found:
            self.lessons.append({
                "goal_pattern": goal_pattern,
                "lessons": [str(e) for e in errors],
                "fail_count": 1,
                "last_seen": datetime.now().strftime("%a %b %d %H:%M:%S %Y")
            })
        
        self._save_lessons()
        logger.info(f"🧠 Auditoria: {len(errors)} lições registradas para o objetivo '{goal_pattern[:30]}...'", symbol="🎓")

    def get_relevant_lessons(self, current_goal: str) -> str:
        """
        Returns a formatted string of lessons that might be relevant to the current goal.
        """
        relevant = []
        for item in self.lessons:
            # Basic keyword matching for relevance
            keywords = [kw for kw in current_goal.lower().split() if len(kw) > 4]
            if any(kw in item["goal_pattern"].lower() for kw in keywords):
                relevant.extend(item["lessons"])
        
        if not relevant:
            # If no direct match, return the 3 most frequent recent fails to keep context sharp
            self.lessons.sort(key=lambda x: x.get("fail_count", 0), reverse=True)
            for item in self.lessons[:2]:
                relevant.extend(item["lessons"][:2])

        if relevant:
            unique_lessons = list(set(relevant))[:10] # Top 10 unique lessons
            return "\n".join([f"- {l}" for l in unique_lessons])
        
        return ""

# Singleton Instance
decision_auditor = DecisionAuditor()
