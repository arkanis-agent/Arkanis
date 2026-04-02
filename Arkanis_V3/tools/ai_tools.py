from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry
from core.llm_client import LLMClient
import os

class AskLLMTool(BaseTool):
    """
    A internal tool that allows the agent to delegate complex text processing, 
    summarization, or extraction to the LLM during execution.
    """
    def __init__(self):
        # We need an LLM Client specifically for the tool layer
        self.llm = LLMClient(api_key=os.environ.get("OPENROUTER_API_KEY"))

    @property
    def name(self) -> str: return "ask_llm"
    
    @property
    def description(self) -> str: 
        return "Process, summarize, or extract information from given text. Useful as a middle-step after fetching data."
    
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "instruction": "The command for the LLM (e.g., 'Summarize this in 3 bullet points').",
            "text_content": "The raw text to be processed (often piped from another tool)."
        }
        
    def execute(self, **kwargs) -> str:
        instruction = kwargs.get("instruction")
        text_content = kwargs.get("text_content")
        
        if not instruction or not text_content:
            return "Error: Missing instruction or text_content."
            
        system_prompt = "You are a sub-processor for ARKANIS OS. Process the user's text strictly according to the instruction. Return ONLY the processed text, without conversational fillers."
        user_prompt = f"INSTRUCTION:\n{instruction}\n\nTEXT TO PROCESS:\n{text_content}"
        
        try:
            response = self.llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
            if response:
                return response
            return "Error: LLM returned empty response."
        except Exception as e:
            return f"Error connecting to LLM: {str(e)}"

# Auto-registration
registry.register(AskLLMTool())
