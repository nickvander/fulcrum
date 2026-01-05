"""
Content Agent - Drafts social media posts based on research.
"""
from typing import Optional
from pathlib import Path
import os

# Conditional ADK imports
try:
    from google.adk.agents import LlmAgent
    ADK_AVAILABLE = True
except ImportError:
    LlmAgent = None
    ADK_AVAILABLE = False


def load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_path = prompts_dir / filename
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


class ContentAgent:
    """
    Agent that drafts social media content.
    """
    
    def __init__(self, model: str = "gemini-3-flash-preview", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self._agent = None
        
        if self.api_key:
            os.environ["GOOGLE_API_KEY"] = self.api_key
            
        self._init_agent()
        
    def _init_agent(self):
        """Initialize the agent."""
        if not ADK_AVAILABLE:
            print("[ContentAgent] ADK not available")
            return
            
        try:
            instruction = load_prompt("content.md")
            
            self._agent = LlmAgent(
                name="marketing_content_writer",
                model=self.model,
                instruction=instruction,
                description="Drafts social media posts for Twitter and Instagram.",
                output_key="content_result"
            )
            print(f"[ContentAgent] Agent initialized with model: {self.model}")
        except Exception as e:
            print(f"[ContentAgent] Init failed: {e}")
            import traceback
            traceback.print_exc()
            self._agent = None
            
    @property
    def adk_agent(self):
        return self._agent
    
    @property
    def is_available(self):
        return ADK_AVAILABLE and self._agent is not None
