from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
from tools.registry import registry
from core.llm_client import LLMClient
import os
import hashlib
import json
import logging
from datetime import datetime, timedelta

class AskLLMCache:
    """Simple in-memory cache for LLM responses to reduce API calls."""
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self._cache: Dict[str, tuple] = {}
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
    
    def _generate_key(self, instruction: str, text_content: str) -> str:
        data = json.dumps({"instruction": instruction, "text_content": text_content}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    def get(self, instruction: str, text_content: str) -> Optional[str]:
        key = self._generate_key(instruction, text_content)
        now = datetime.now()
        if key in self._cache:
            response, timestamp = self._cache[key]
            if now - timestamp < self.ttl:
                return response
            del self._cache[key]
        return None
    
    def set(self, instruction: str, text_content: str, response: str):
        if len(self._cache) >= self.max_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        key = self._generate_key(instruction, text_content)
        self._cache[key] = (response, datetime.now())

# Initialize cache at module level
_llm_cache = AskLLMCache()

class AskLLMTool(BaseTool):
    """
    A internal tool that allows the agent to delegate complex text processing, 
    summarization, or extraction to the LLM during execution.
    """
    def __init__(self):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logging.warning("OPENROUTER_API_KEY not found. AskLLMTool may not function correctly.")
            self.llm = None
        else:
            self.llm = LLMClient(api_key=api_key)
            
        # Class-level cache shared across instances
        self._cache = _llm_cache

    @property
    def name(self) -> str:
        return "ask_llm"
    
    @property
    def description(self) -> str:
        return "Process, summarize, or extract information from given text. Useful as a middle-step after fetching data."
    
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "instruction": str,
            "text_content": str
        }
        
    def execute(self, instruction: str, text_content: str) -> str:
        """Process text through LLM with caching and proper error handling."""
        
        # Validate inputs
        if not instruction or not instruction.strip():
            logging.error("AskLLMTool: instruction is required")
            return "Error: Missing instruction."
            
        if not text_content or not text_content.strip():
            logging.error("AskLLMTool: text_content is required")
            return "Error: Missing text_content."
            
        # Check LLM availability
        if not self.llm:
            return "Error: LLM Client not initialized. Check API_KEY environment variable."
            
        # Attempt cache retrieval
        cached_response = self._cache.get(instruction, text_content)
        if cached_response:
            return cached_response
            
        system_prompt = "You are a sub-processor for ARKANIS OS. Process the user's text strictly according to the instruction. Return ONLY the processed text, without conversational fillers."
        user_prompt = f"INSTRUCTION:\n{instruction}\n\nTEXT TO PROCESS:\n{text_content}"
        
        try:
            response = self.llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
            if response and response.strip():
                self._cache.set(instruction, text_content, response)
                return response
            return "Error: LLM returned empty response."
        except Exception as e:
            logging.error(f"LLM Generation Error: {str(e)}")
            return f"Error connecting to LLM: {type(e).__name__}"

# Auto-registration
registry.register(AskLLMTool())
