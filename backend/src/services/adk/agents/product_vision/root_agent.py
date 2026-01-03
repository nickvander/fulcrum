"""
Product Vision Root Agent.
Orchestrates the vision analysis workflow.
"""
import base64
import json
from typing import Dict, Any
from pathlib import Path

from google.adk.runners import Runner
from backend.src.services.adk.agents.product_vision.vision_agent import VisionAnalysisAgent

class ProductVisionRootAgent:
    """
    Root agent for the Product Vision capability.
    Coordinates sub-agents (currently just VisionAnalysisAgent) to fulfill requests.
    """
    
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.vision_worker = VisionAnalysisAgent(model)
        
    async def identify(self, image_path: str) -> Dict[str, Any]:
        """
        Identify a product from an image using the vision worker.
        """
        if not self.vision_worker.adk_agent:
             return {"error": "ADK agent not initialized", "name": "Unknown"}

        try:
            # Read image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Delegate to worker via Runner
            runner = Runner(agent=self.vision_worker.adk_agent)
            
            result = await runner.run_async(
                user_id="system",
                session_id="product_scan_root",
                new_message={
                    "role": "user",
                    "parts": [
                        {"text": "Identify this product and return JSON."},
                        {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                    ]
                }
            )
            
            if result and result.response:
                return self._parse_response(result.response.text)
            
            return {"error": "No response", "name": "Unknown"}
            
        except Exception as e:
            return {"error": str(e), "name": "Unknown"}

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response."""
        try:
            clean = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            return {"name": "Unknown", "description": text}
