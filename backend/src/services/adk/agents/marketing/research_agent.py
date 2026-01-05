"""
Research Agent - Finds trends and product info using Google Search.
"""
from typing import Optional
from pathlib import Path
import os

# Conditional ADK imports
try:
    from google.adk.agents import LlmAgent
    from google.adk.tools import GoogleSearch
    ADK_AVAILABLE = True
except ImportError:
    LlmAgent = None
    GoogleSearch = None
    ADK_AVAILABLE = False


def load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_path = prompts_dir / filename
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


class ResearchAgent:
    """
    Agent that researches products and trends using Google Search.
    """
    
    def __init__(self, model: str = "gemini-3-flash-preview", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self._agent = None
        
        if self.api_key:
            os.environ["GOOGLE_API_KEY"] = self.api_key
            
        self._init_agent()
        
    def _init_agent(self):
        """Initialize the agent with Google Search tool."""
        if not ADK_AVAILABLE:
            print("[ResearchAgent] ADK not available")
            return
            
        try:
            # Initialize Google Search tool
            # Note: This requires the google-search-results or similar package installed depending on ADK version,
            # but usually ADK's GoogleSearch wraps the engine. 
            # Assuming standard ADK usage where tool is initialized.
            search_tool = GoogleSearch()
            
            instruction = load_prompt("research.md")
            
            self._agent = LlmAgent(
                name="marketing_research",
                model=self.model,
                instruction=instruction,
                description="Researches market trends and product details.",
                tools=[search_tool],
                output_key="research_result"
            )
            print(f"[ResearchAgent] Agent initialized with model: {self.model}")
        except Exception as e:
            print(f"[ResearchAgent] Init failed: {e}")
            import traceback
            traceback.print_exc()
            self._agent = None
            
    @property
    def adk_agent(self):
        return self._agent
    
    @property
    def is_available(self):
        return ADK_AVAILABLE and self._agent is not None
