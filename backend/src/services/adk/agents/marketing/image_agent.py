"""
Image Agent - Generates prompts for AI image generation.
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


class ImageAgent:
    """
    Agent that designs image concepts and generates prompts for image generation models.
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
            print("[ImageAgent] ADK not available")
            return
            
        try:
            instruction = load_prompt("image_generation.md")
            
            self._agent = LlmAgent(
                name="marketing_art_director",
                model=self.model,
                instruction=instruction,
                description="Generates detailed prompts for marketing images.",
                output_key="image_result"
            )
            print(f"[ImageAgent] Agent initialized with model: {self.model}")
        except Exception as e:
            print(f"[ImageAgent] Init failed: {e}")
            import traceback
            traceback.print_exc()
            self._agent = None
            
    @property
    def adk_agent(self):
        return self._agent
    
    @property
    def is_available(self):
        return ADK_AVAILABLE and self._agent is not None
