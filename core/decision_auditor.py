import os
import json
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("uvicorn")


class DecisionAuditor:
    """
    ARKANIS V3.1 - Autonomous Decision Auditor
    Tracks agent failures and successes to build a persistent 'Lessons Learned' database.
    Thread-safe implementation with optimized lookups.
    """
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.lessons_file = os.path.join(self.base_dir, "data", "critic_lessons.json")
        self.lessons = self._load_lessons()
        self._lock = threading.RLock()  # Thread safety for file operations
        self._cache = {}  # Cache for faster goal pattern lookups

    def _load_lessons(self) -> Dict[str, Dict[str, Any]]:
        """Loads lessons and converts to O(1) lookup dictionary."""
        if os.path.exists(self.lessons_file):
            try:
                with open(self.lessons_file, "r", encoding="utf-8") as f:
                    raw_lessons = json.load(f)
                    # Convert to dict keyed by goal_pattern for O(1) lookup
                    return {item["goal_pattern"]: item for item in raw_lessons}
            except Exception as e:
                logger.error(f"Failed to load lessons: {e}")
        return {}

    def _save_lessons(self):
        """Thread-safe file operation with lock."""
        with self._lock:
            try:
                with open(self.lessons_file, "w", encoding="utf-8") as f:
                    json.dump(list(self.lessons.values()), f, indent=4, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to save lessons: {e}")

    def _normalize_pattern(self, pattern: str) -> str:
        """Normalize string for comparison - handles whitespace and case."""
        return " ".join(pattern.strip().lower().split())

    def _find_similar_pattern(self, goal: str) -> Optional[str]:
        """Find similar pattern with fuzzy matching."""
        goal_normalized = self._normalize_pattern(goal)
        if goal_normalized in self._cache:
            return goal_normalized
        
        # Simple similarity: check if goal contains pattern keywords
        goal_words = {w for w in goal_normalized.split() if len(w) > 3}
        for pattern in self._cache.keys():
            pattern_words = {w for w in pattern.split() if len(w) > 3}
            if goal_words & pattern_words:  # Intersection
                return pattern
        
        self._cache[goal_normalized] = goal_normalized
        return None

    def record_lesson(self, goal: str, results: List[str]):
        """Records lessons from failed execution with thread safety."""
        if not goal or not isinstance(results, list):
            logger.warning("Invalid parameters for record_lesson")
            return

        errors = [
            r for r in results 
            if "[Error]" in str(r) or "failha" in str(r).lower() 
               or "error" in str(r).lower()
        ]
        if not errors:
            return

        goal_pattern = self._normalize_pattern(goal)
        existing_pattern = self._find_similar_pattern(goal) or goal_pattern

        with self._lock:
            if existing_pattern in self._lessons:
                # Add new unique errors as lessons
                for err in errors:
                    clean_err = str(err).split(":", 1)[-1].strip() if ":" in str(err) else str(err)
                    if clean_err not in self._lessons[existing_pattern]["lessons"]:
                        self._lessons[existing_pattern]["lessons"].append(clean_err)
                self._lessons[existing_pattern]["fail_count"] = self._lessons[existing_pattern].get("fail_count", 0) + 1
                self._lessons[existing_pattern]["last_seen"] = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
            else:
                self._lessons[existing_pattern] = {
                    "goal_pattern": existing_pattern,
                    "lessons": [str(e) for e in errors],
                    "fail_count": 1,
                    "last_seen": datetime.now().strftime("%a %b %d %H:%M:%S %Y")
                }
            
            self._save_lessons()
            logger.info(f"🧠 Auditoria: {len(errors)} lições registradas para '{goal[:30]}...'", extra={"symbol": "🎓"})

    def get_relevant_lessons(self, current_goal: str) -> str:
        """Returns formatted relevant lessons with fuzzy matching and limits."""
        if not current_goal or len(current_goal.strip()) < 5:
            return ""
        
        relevant = []
        current_words = [kw for kw in current_goal.lower().split() if len(kw) > 4]

        with self._lock:
            for pattern, item in self._lessons.items():
                if any(kw in self._normalize_pattern(pattern) for kw in current_words):
                    relevant.extend(item["lessons"][:3])  # Limit per pattern

            if not relevant:
                # Fallback: most frequent recent fails
                sorted_lessons = sorted(
                    self._lessons.items(), 
                    key=lambda x: x[1].get("fail_count", 0), 
                    reverse=True
                )
                for pattern, item in sorted_lessons[:2]:
                    relevant.extend(item["lessons"][:2])

            if relevant:
                unique_lessons = list(dict.fromkeys(relevant))[:10]  # Preserve order, unique
                return "\n".join([f"- {l}" for l in unique_lessons])
        
        return ""

    def cleanup_old_lessons(self, max_lessons: int = 50, max_age_days: int = 90):
        """Remove old or infrequent lessons to manage memory."""
        with self._lock:
            now = datetime.now()
            threshold = datetime(now.year, now.month, now.day)
            
            for pattern, item in list(self._lessons.items()):
                # Remove by frequency
                if item.get("fail_count", 0) == 0:
                    del self._lessons[pattern]
                    continue
                
                # Remove by age
                try:
                    last_seen = datetime.strptime(item["last_seen"], "%a %b %d %H:%M:%S %Y")
                    if (now - last_seen).days > max_age_days:
                        del self._lessons[pattern]
                        continue
                except ValueError:
                    continue
            
            # Trim to max size if needed
            if len(self._lessons) > max_lessons:
                sorted_lessons = sorted(
                    self._lessons.items(),
                    key=lambda x: x[1].get("fail_count", 0),
                    reverse=True
                )
                to_keep = dict(sorted_lessons[:max_lessons])
                self._lessons = to_keep
            
            self._save_lessons()
            logger.info(f"Cleanup: {len(self._lessons)} lições ativas")

    def clear_lessons(self):
        """Safely clear all lessons."""
        with self._lock:
            self._lessons.clear()
            self._cache.clear()
            self._save_lessons()
            logger.info("Todas as lições foram limpas.")


# Thread-safe singleton - lazy initialization for testing flexibility
class _SingletonMeta(type):
    _instance = None
    _lock = threading.Lock()
    
    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


class DecisionAuditor(metaclass=_SingletonMeta):
    """Singleton implementation for thread-safe global instance."""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.lessons_file = os.path.join(self.base_dir, "data", "critic_lessons.json")
        self._lock = threading.RLock()
        self.lessons = {}
        self._cache = {}
        self._init_cache()  # Lazy load pattern cache
        
    def _init_cache(self):
        """Initialize lessons with O(1) lookup structure."""
        with self._lock:
            if not self.lessons:
                try:
                    if os.path.exists(self.lessons_file):
                        with open(self.lessons_file, "r", encoding="utf-8") as f:
                            raw_lessons = json.load(f)
                            self.lessons = {item["goal_pattern"]: item for item in raw_lessons}
                except Exception as e:
                    logger.error(f"Failed to load lessons: {e}")

    def _load_lessons(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            if os.path.exists(self.lessons_file):
                try:
                    with open(self.lessons_file, "r", encoding="utf-8") as f:
                        raw_lessons = json.load(f)
                        return {item["goal_pattern"]: item for item in raw_lessons}
                except Exception as e:
                    logger.error(f"Failed to load lessons: {e}")
            return {}

    def _save_lessons(self):
        with self._lock:
            try:
                with open(self.lessons_file, "w", encoding="utf-8") as f:
                    json.dump(list(self.lessons.values()), f, indent=4, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to save lessons: {e}")

    def _normalize_pattern(self, pattern: str) -> str:
        return " ".join(pattern.strip().lower().split())

    def _find_similar_pattern(self, goal: str) -> Optional[str]:
        goal_normalized = self._normalize_pattern(goal)
        goal_words = {w for w in goal_normalized.split() if len(w) > 3}
        for pattern in self.lessons.keys():
            pattern_words = {w for w in pattern.split() if len(w) > 3}
            if goal_words & pattern_words:
                return pattern
        self._cache[goal_normalized] = goal_normalized
        return None

    def record_lesson(self, goal: str, results: List[str]):
        if not goal or not isinstance(results, list):
            logger.warning("Invalid parameters for record_lesson")
            return

        errors = [
            r for r in results
            if "[Error]" in str(r) or "falha" in str(r).lower() or "error" in str(r).lower()
        ]
        if not errors:
            return

        goal_pattern = self._normalize_pattern(goal)
        existing_pattern = self._find_similar_pattern(goal) or goal_pattern

        with self._lock:
            if existing_pattern in self.lessons:
                for err in errors:
                    clean_err = str(err).split(":", 1)[-1].strip() if ":" in str(err) else str(err)
                    if clean_err not in self.lessons[existing_pattern]["lessons"]:
                        self.lessons[existing_pattern]["lessons"].append(clean_err)
                self.lessons[existing_pattern]["fail_count"] = self.lessons[existing_pattern].get("fail_count", 0) + 1
                self.lessons[existing_pattern]["last_seen"] = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
            else:
                self.lessons[existing_pattern] = {
                    "goal_pattern": existing_pattern,
                    "lessons": [str(e) for e in errors],
                    "fail_count": 1,
                    "last_seen": datetime.now().strftime("%a %b %d %H:%M:%S %Y")
                }
            self._save_lessons()
            logger.info(f"🧠 Auditoria: {len(errors)} lições registradas para '{goal[:30]}...'", extra={"symbol": "🎓"})

    def get_relevant_lessons(self, current_goal: str) -> str:
        if not current_goal or len(current_goal.strip()) < 5:
            return ""
        
        relevant = []
        current_words = [kw for kw in current_goal.lower().split() if len(kw) > 4]

        with self._lock:
            for pattern, item in self.lessons.items():
                if any(kw in self._normalize_pattern(pattern) for kw in current_words):
                    relevant.extend(item["lessons"][:3])

            if not relevant:
                sorted_lessons = sorted(
                    self.lessons.items(),
                    key=lambda x: x[1].get("fail_count", 0),
                    reverse=True
                )
                for pattern, item in sorted_lessons[:2]:
                    relevant.extend(item["lessons"][:2])

            if relevant:
                unique_lessons = list(dict.fromkeys(relevant))[:10]
                return "\n".join([f"- {l}" for l in unique_lessons])
        
        return ""

    def cleanup_old_lessons(self, max_lessons: int = 50, max_age_days: int = 90):
        with self._lock:
            now = datetime.now()
            threshold = datetime(now.year, now.month, now.day)
            
            for pattern, item in list(self.lessons.items()):
                if item.get("fail_count", 0) == 0:
                    del self.lessons[pattern]
                    continue
                
                try:
                    last_seen = datetime.strptime(item["last_seen"], "%a %b %d %H:%M:%S %Y")
                    if (now - last_seen).days > max_age_days:
                        del self.lessons[pattern]
                        continue
                except ValueError:
                    continue
            
            if len(self.lessons) > max_lessons:
                sorted_lessons = sorted(
                    self.lessons.items(),
                    key=lambda x: x[1].get("fail_count", 0),
                    reverse=True
                )
                to_keep = dict(sorted_lessons[:max_lessons])
                self.lessons = to_keep
            
            self._save_lessons()
            logger.info(f"Cleanup: {len(self.lessons)} lições ativas")

    def clear_lessons(self):
        with self._lock:
            self.lessons.clear()
            self._cache.clear()
            self._save_lessons()
            logger.info("Todas as lições foram limpas.")


# Lazy singleton instance
def _get_auditor():
    try:
        return globals()["_AUDITOR_INSTANCE"]
    except KeyError:
        import threading
        if not hasattr(_get_auditor, "_initialized"):
            _AUDITOR_INSTANCE = None
            _get_auditor._initialized = True
        return _AUDITOR_INSTANCE

# Module-level lazy singleton
_auditor_instance = None
class _SingletonMetaForAuditor(type):
    _lock = threading.Lock()
    
    __call__ = lambda cls, *args, **kwargs: \
        cls._instance if cls._instance else type._new(cls, lambda *a, **k: \
            (hasattr(cls._lock, "__enter__") and \
             (cls.__dict__._instance is cls._new(cls) or \
              (cls.__dict__._instance))))

_auditor_lock = threading.Lock()
_auditor_instance = None

def get_decision_auditor():
    global _auditor_instance
    with _auditor_lock:
        if _auditor_instance is None:
            import arkanis_v3.core.decision_auditor as da
            _auditor_instance = da.DecisionAuditor()
        return _auditor_instance

# Backwards compatibility for existing imports
decision_auditor = None
def __getattr__(name):
    if name == "decision_auditor":
        global decision_auditor
        if decision_auditor is None:
            import threading
            _auditor_lock = threading.Lock()
        return get_decision_auditor()
    raise AttributeError(f"module has no attribute {name}")