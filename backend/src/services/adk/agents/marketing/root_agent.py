"""
Marketing Root Agent - Orchestrates the full content generation pipeline.
Pipeline: Research -> Content Drafting -> Image Prompting
"""
import json
import os
from typing import Dict, Any
from pathlib import Path

# Conditional ADK imports
try:
    from google.adk.agents import SequentialAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from google.genai import Client
    ADK_AVAILABLE = True
except ImportError:
    SequentialAgent = None
    Runner = None
    InMemorySessionService = None
    types = None
    Client = None
    ADK_AVAILABLE = False

from .research_agent import ResearchAgent
from .content_agent import ContentAgent
from .image_agent import ImageAgent


class MarketingRootAgent:
    """
    Orchestrator for Marketing Content Generation.
    
    Capabilities:
    1. Research product & trends (ResearchAgent)
    2. Draft social media content (ContentAgent)
    3. Design image concepts (ImageAgent)
    4. Generate actual images (via google-genai SDK if available)
    """
    
    def __init__(self, model: str = "gemini-3-flash-preview", api_key: str = None):
        self.model = model
        self.api_key = api_key
        self._pipeline = None
        self._session_service = None
        
        # Sub-agents
        self.research_agent = None
        self.content_agent = None
        self.image_agent = None
        
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
            
        self._init_services()
        self._init_pipeline()
        
    def _init_services(self):
        """Initialize ADK services."""
        if not ADK_AVAILABLE:
            return
        self._session_service = InMemorySessionService()
        
    def _init_pipeline(self):
        """Initialize the sequential agent pipeline."""
        if not ADK_AVAILABLE:
            return
            
        try:
            # Create sub-agents
            self.research_agent = ResearchAgent(self.model, self.api_key)
            self.content_agent = ContentAgent(self.model, self.api_key)
            self.image_agent = ImageAgent(self.model, self.api_key)
            
            sub_agents = []
            if self.research_agent.is_available:
                sub_agents.append(self.research_agent.adk_agent)
            if self.content_agent.is_available:
                sub_agents.append(self.content_agent.adk_agent)
            if self.image_agent.is_available:
                sub_agents.append(self.image_agent.adk_agent)
                
            if not sub_agents:
                print("[MarketingRoot] No sub-agents available")
                return
            
            # Create sequential pipeline
            self._pipeline = SequentialAgent(
                name="marketing_pipeline",
                sub_agents=sub_agents
            )
            print("[MarketingRoot] Pipeline initialized")
            
        except Exception as e:
            print(f"[MarketingRoot] Pipeline init failed: {e}")
            import traceback
            traceback.print_exc()
            self._pipeline = None
            
    @property
    def is_available(self) -> bool:
        return ADK_AVAILABLE and self._pipeline is not None
        
    async def generate_campaign(self, 
                              product_name: str, 
                              product_description: str,
                              platform: str = "Twitter",
                              generate_image: bool = True,
                              product_image_url: str = None) -> Dict[str, Any]:
        """
        Run the full generation pipeline.
        
        Args:
            product_name: Name of the product
            product_description: Product description
            platform: Target platform (Twitter, Instagram)
            generate_image: Whether to generate an image
            product_image_url: Optional URL to existing product image for style reference
        """
        if not self.is_available:
            return {"error": "ADK pipeline not available"}
            
        try:
            # Create session
            import uuid
            session_id = f"mkt_{uuid.uuid4().hex[:8]}"
            await self._session_service.create_session(
                app_name="fulcrum_marketing",
                user_id="system",
                session_id=session_id
            )
            
            # Construct the user prompt with product image reference
            image_context = ""
            if product_image_url:
                image_context = f"\nProduct Image URL: {product_image_url}\n(Use this as style reference for generated images)"
            
            prompt_text = (
                f"Create a {platform} marketing post for the following product.\n\n"
                f"Product: {product_name}\n"
                f"Description: {product_description}{image_context}\n\n"
                f"Please research current trends first, then draft the content, "
                f"and finally design an image concept."
            )
            
            user_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt_text)]
            )
            
            runner = Runner(
                agent=self._pipeline,
                session_service=self._session_service,
                app_name="fulcrum_marketing"
            )
            
            print(f"[MarketingRoot] Starting pipeline for {product_name} on {platform}...")
            
            # Run pipeline
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=user_content
            ):
                pass # collecting state mainly
                
            # Retrieve state
            session = await self._session_service.get_session(
                app_name="fulcrum_marketing",
                user_id="system",
                session_id=session_id
            )
            
            state = session.state
            result = {
                "research": self._parse_json(state.get("research_result", "{}")),
                "content": self._parse_json(state.get("content_result", "{}")),
                "image_concept": self._parse_json(state.get("image_result", "{}")),
                "generated_image_url": None
            }
            
            # Try to generate actual image if requested
            if generate_image and result["image_concept"]:
                prompt = result["image_concept"].get("image_prompt")
                if prompt:
                    result["generated_image_url"] = await self._generate_real_image(prompt)
            
            return result
            
        except Exception as e:
            print(f"[MarketingRoot] Execution error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
            
    async def _generate_real_image(self, prompt: str) -> str:
        """Generate an image using Gemini's native image generation via generate_content."""
        if ADK_AVAILABLE and Client and self.api_key:
            try:
                # Append stylistic instructions to the prompt
                enhanced_prompt = (
                    f"{prompt} "
                    "Make the image photorealistic, high quality, shot on a Google Pixel 10, "
                    "natural lighting, cinematic composition."
                )

                print(f"[MarketingRoot] Generating image with gemini-2.0-flash-exp via generate_content for prompt: {enhanced_prompt[:50]}...")
                client = Client(api_key=self.api_key)
                
                # Use generate_content with response_modalities to get image output
                response = client.models.generate_content(
                    model='gemini-2.0-flash-exp',
                    contents=enhanced_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=['IMAGE', 'TEXT'],
                    )
                )
                
                # Extract image from response parts
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            # This is an image part
                            image_data = part.inline_data
                            if hasattr(image_data, 'data') and image_data.data:
                                from datetime import datetime
                                
                                # Ensure directory exists in uploads (mounted by FastAPI)
                                output_dir = Path("uploads/generated")
                                output_dir.mkdir(parents=True, exist_ok=True)
                                
                                filename = f"gen_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                                output_path = output_dir / filename
                                
                                with open(output_path, "wb") as f:
                                    f.write(image_data.data)
                                    
                                print(f"[MarketingRoot] Image saved to {output_path}")
                                return f"/uploads/generated/{filename}"
                                
                print("[MarketingRoot] No image found in response")
                         
            except Exception as e:
                print(f"[MarketingRoot] Image generation failed: {e}")
                import traceback
                traceback.print_exc()
        
        return "assets/images/placeholder_generated.png" # Fallback
        
    def _parse_json(self, text: str) -> Any:
        try:
            if isinstance(text, dict):
                return text
            clean = text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            return json.loads(clean.strip())
        except Exception:
            return text
