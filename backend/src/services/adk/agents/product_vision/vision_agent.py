"""
Vision Analysis Agent - Analyzes product images.
Sub-agent for the product identification pipeline.
"""
from typing import Optional
from pathlib import Path

# Conditional ADK imports
try:
    from google.adk.agents import Agent
    ADK_AVAILABLE = True
except ImportError:
    Agent = None
    ADK_AVAILABLE = False


def load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_path = prompts_dir / filename
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


class VisionAnalysisAgent:
    """
    Agent for analyzing product images.
    Outputs structured JSON with product details.
    Uses output_key to save results to session state for next agent.
    """
    
    def __init__(self, model: str = "gemini-2.0-flash", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self._agent = None
        
        # Set API key in environment
        if self.api_key:
            import os
            os.environ["GOOGLE_API_KEY"] = self.api_key
            print(f"[VisionAgent] API key set (length: {len(self.api_key)})")
            
        self._init_agent()
        
    def _init_agent(self):
        """Initialize the vision agent."""
        if not ADK_AVAILABLE:
            print("[VisionAgent] ADK not available")
            return
            
        try:
            system_prompt = load_prompt("system.md")
            
            # Simple vision agent - no tools, just image analysis
            # Uses output_key to save result to state for the lookup agent
            self._agent = Agent(
                name="vision_analysis",
                model=self.model,
                description="Analyzes product images to extract attributes.",
                instruction=system_prompt,
                output_key="vision_result"  # Saves response to state["vision_result"]
            )
            print(f"[VisionAgent] Agent initialized with model: {self.model}")
        except Exception as e:
            print(f"[VisionAgent] Init failed: {e}")
            import traceback
            traceback.print_exc()
            self._agent = None

    @property
    def adk_agent(self):
        return self._agent
    
    @property
    def is_available(self):
        return ADK_AVAILABLE and self._agent is not None
