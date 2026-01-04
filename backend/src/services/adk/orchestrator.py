"""
ADK Orchestrator

Manages the execution of sequential agent workflows.
Orchestrates the flow between specialized agents (e.g. Vision -> Pricing -> Content).
"""
from typing import Dict, Any, List
from .manager import ADKManager

# Import agents
from .agents.product_vision.agent import ProductVisionAgent

class AgentOrchestrator:
    """
    Orchestrates sequential agent execution.
    """
    
    def __init__(self, manager: ADKManager):
        self.manager = manager
        
    async def process_product_image(self, image_path: str) -> Dict[str, Any]:
        """
        Run the product intake workflow:
        1. Identify product from image (Vision Agent)
        2. (Future) Search for pricing (Pricing Agent)
        3. (Future) Generate marketing content (Content Agent)
        """
        
        # 1. Vision Analysis
        vision_agent = self._get_vision_agent()
        vision_result = await vision_agent.identify(image_path)
        
        if "error" in vision_result:
            return vision_result
            
        # For now, just return the vision result
        # Future: Pass result to next agent in sequence
        return vision_result
        
    def _get_vision_agent(self) -> ProductVisionAgent:
        """Get configured vision agent."""
        config = self.manager.get_active_config()
        return ProductVisionAgent(model=config.get("model"), api_key=config.get("api_key"))

    async def run_sequence(self, input_data: Any, agents: List[Any]) -> Any:
        """Generic sequential runner."""
        result = input_data
        for agent in agents:
            # Assumes standard interface: agent.process(data)
            if hasattr(agent, 'process'):
                result = await agent.process(result)
            elif hasattr(agent, 'identify'): # Vision agent
                result = await agent.identify(result)
        return result
