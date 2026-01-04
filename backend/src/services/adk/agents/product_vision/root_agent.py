"""
Product Vision Root Agent - Orchestrates the product identification pipeline.
Uses ADK SequentialAgent to run: Vision → Lookup
"""
import json
import re
import os
from typing import Dict, Any
from pathlib import Path

# Conditional ADK imports
try:
    from google.adk.agents import SequentialAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    SequentialAgent = None
    Runner = None
    InMemorySessionService = None
    types = None
    ADK_AVAILABLE = False

from .vision_agent import VisionAnalysisAgent
from .lookup_agent import ProductLookupAgent


class ProductVisionRootAgent:
    """
    Root orchestrator for the Product Vision capability.
    Uses SequentialAgent to run: Vision Agent → Lookup Agent
    
    Flow:
    1. Vision Agent analyzes image → saves to state["vision_result"]
    2. Lookup Agent reads state → checks database → returns final result
    """
    
    def __init__(self, model: str = "gemini-2.0-flash", api_key: str = None):
        self.model = model
        self.api_key = api_key
        self._pipeline = None
        self._session_service = None
        self._vision_agent = None
        self._lookup_agent = None
        
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
            print(f"[RootAgent] API key set (length: {len(api_key)})")
            
        self._init_services()
        self._init_pipeline()
        
    def _init_services(self):
        """Initialize ADK services."""
        if not ADK_AVAILABLE:
            print("[RootAgent] ADK not available")
            return
            
        self._session_service = InMemorySessionService()
        print("[RootAgent] Session service initialized")
        
    def _init_pipeline(self):
        """Initialize the sequential agent pipeline."""
        if not ADK_AVAILABLE:
            return
            
        try:
            # Create sub-agents
            self._vision_agent = VisionAnalysisAgent(self.model, self.api_key)
            self._lookup_agent = ProductLookupAgent(self.model)
            
            if not self._vision_agent.is_available:
                print("[RootAgent] Vision agent not available")
                return
                
            if not self._lookup_agent.is_available:
                print("[RootAgent] Lookup agent not available")
                return
            
            # Create sequential pipeline: Vision → Lookup
            self._pipeline = SequentialAgent(
                name="product_pipeline",
                sub_agents=[
                    self._vision_agent.adk_agent,
                    self._lookup_agent.adk_agent
                ]
            )
            print("[RootAgent] Pipeline created: Vision → Lookup")
            
        except Exception as e:
            print(f"[RootAgent] Pipeline init failed: {e}")
            import traceback
            traceback.print_exc()
            self._pipeline = None
        
    @property
    def is_available(self) -> bool:
        return ADK_AVAILABLE and self._pipeline is not None
        
    async def identify(self, image_path: str) -> Dict[str, Any]:
        """
        Identify a product from an image using the sequential pipeline.
        
        Flow:
        1. Vision agent analyzes image
        2. Lookup agent checks database
        3. Returns combined result
        """
        if not self.is_available:
            return {"error": "ADK pipeline not available", "name": "Unknown"}
            
        try:
            # Read image
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            # Determine MIME type  
            ext = Path(image_path).suffix.lower()
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp"
            }.get(ext, "image/jpeg")
            
            # Create runner for the pipeline
            runner = Runner(
                agent=self._pipeline,
                session_service=self._session_service,
                app_name="fulcrum_vision"
            )
            
            # Create session
            import uuid
            session_id = f"scan_{uuid.uuid4().hex[:8]}"
            await self._session_service.create_session(
                app_name="fulcrum_vision",
                user_id="system",
                session_id=session_id
            )
            
            # Build message with image as inlineData
            user_content = types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text="Analyze this product image and check if it exists in our database."),
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                ]
            )
            
            # Run the pipeline
            print("[RootAgent] Running pipeline...")
            final_text = None
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=user_content
            ):
                author = getattr(event, 'author', None)
                is_final = event.is_final_response()
                print(f"[RootAgent] Event: author={author}, is_final={is_final}")
                
                # Get text from event content
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            final_text = part.text
                            print(f"[RootAgent] Got text from {author}: {final_text[:100]}...")
            
            # Try to get results from session state
            if not final_text:
                try:
                    session = await self._session_service.get_session(
                        app_name="fulcrum_vision",
                        user_id="system", 
                        session_id=session_id
                    )
                    if session and hasattr(session, 'state'):
                        # Try lookup_result first (final step), then vision_result
                        if 'lookup_result' in session.state:
                            final_text = session.state['lookup_result']
                            print("[RootAgent] Got lookup_result from state")
                        elif 'vision_result' in session.state:
                            final_text = session.state['vision_result']
                            print("[RootAgent] Got vision_result from state")
                except Exception as e:
                    print(f"[RootAgent] State lookup error: {e}")
            
            if final_text:
                return self._parse_response(final_text)
            
            return {"error": "No response from pipeline", "name": "Unknown"}
            
        except Exception as e:
            print(f"[RootAgent] Error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "name": "Unknown"}

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response from agents."""
        try:
            # First try parsing everything (cleanest case)
            clean = text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            try:
                # If that fails, try regex to find the first JSON object block
                # This matches { ... } including nested braces
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                print(f"[RootAgent] Regex JSON parse error: {e}")
            
            # Return as description if not valid JSON
            return {"name": "Unknown", "description": text}
