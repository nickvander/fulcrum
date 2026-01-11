"""
Description Agent - Generates product marketing descriptions via ADK.
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


class DescriptionAgent:
    """
    Agent that generates product marketing descriptions.
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
            print("[DescriptionAgent] ADK not available")
            return
            
        try:
            instruction = load_prompt("description.md")
            
            self._agent = LlmAgent(
                name="product_description_writer",
                model=self.model,
                instruction=instruction,
                description="Generates compelling product descriptions for e-commerce.",
                output_key="description_result"
            )
            print(f"[DescriptionAgent] Agent initialized with model: {self.model}")
        except Exception as e:
            print(f"[DescriptionAgent] Init failed: {e}")
            import traceback
            traceback.print_exc()
            self._agent = None
            
    @property
    def adk_agent(self):
        return self._agent
    
    @property
    def is_available(self):
        return ADK_AVAILABLE and self._agent is not None
