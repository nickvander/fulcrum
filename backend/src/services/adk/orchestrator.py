"""
ADK Orchestrator

Manages the execution of sequential agent workflows.
Orchestrates the flow between specialized agents (e.g. Vision -> Pricing -> Content).
"""
from typing import Dict, Any, List, Optional
from .manager import ADKManager

# Import agents
from .agents.product_vision.agent import ProductVisionAgent
from .agents.marketing.description_agent import DescriptionAgent
from .agents.invoice.invoice_parser_agent import InvoiceParserAgent

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

    async def generate_product_description(
        self, 
        product_name: str, 
        context: Optional[str] = None,
        tone: Optional[str] = None,
        length: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a marketing description for a product using the DescriptionAgent.
        
        Args:
            product_name: Name of the product
            context: Additional context (category, brand, features, etc.)
            tone: Desired tone (e.g., "Professional", "Casual", "Luxury")
            length: Desired length (e.g., "short", "medium", "long")
            
        Returns:
            Dict with 'description', 'seo_keywords', 'tone_used', or 'error'
        """
        try:
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types
            import uuid
            import json
            
            agent = self._get_description_agent()
            if not agent.is_available:
                return {"error": "Description agent not available"}
            
            # Create session
            session_service = InMemorySessionService()
            session_id = f"desc_{uuid.uuid4().hex[:8]}"
            await session_service.create_session(
                app_name="fulcrum_description",
                user_id="system",
                session_id=session_id
            )
            
            # Build the prompt
            prompt_parts = [f"Generate a product description for: {product_name}"]
            if context:
                prompt_parts.append(f"Context: {context}")
            if tone:
                prompt_parts.append(f"Tone: {tone}")
            if length:
                prompt_parts.append(f"Length: {length}")
            
            prompt_text = "\n".join(prompt_parts)
            
            user_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt_text)]
            )
            
            runner = Runner(
                agent=agent.adk_agent,
                session_service=session_service,
                app_name="fulcrum_description"
            )
            
            print(f"[Orchestrator] Generating description for: {product_name}")
            
            # Run agent
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=user_content
            ):
                pass
            
            # Retrieve state
            session = await session_service.get_session(
                app_name="fulcrum_description",
                user_id="system",
                session_id=session_id
            )
            
            result_text = session.state.get("description_result", "{}")
            
            # Parse JSON result
            try:
                if isinstance(result_text, dict):
                    return result_text
                clean = result_text.strip()
                if clean.startswith("```json"):
                    clean = clean[7:]
                if clean.startswith("```"):
                    clean = clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
                return json.loads(clean.strip())
            except json.JSONDecodeError:
                # Return raw text as description if not JSON
                return {"description": result_text, "seo_keywords": [], "tone_used": tone or "neutral"}
            
        except Exception as e:
            print(f"[Orchestrator] Description generation error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _get_description_agent(self) -> DescriptionAgent:
        """Get configured description agent."""
        config = self.manager.get_active_config()
        return DescriptionAgent(model=config.get("model"), api_key=config.get("api_key"))

    async def parse_invoice(
        self, 
        file_content: bytes, 
        file_type: str
    ) -> Dict[str, Any]:
        """
        Parse an invoice document and extract structured data.
        
        Args:
            file_content: Raw bytes of the invoice file
            file_type: MIME type (e.g., 'application/pdf', 'image/png')
            
        Returns:
            Dict with extracted invoice data including:
            - vendor_name, invoice_number, invoice_date
            - items: list of line items with sku, description, quantity, unit_cost, line_total
            - subtotal, tax_amount, shipping_cost, total_amount
            - confidence: float between 0 and 1
        """
        try:
            agent = self._get_invoice_parser_agent()
            if not agent.is_available:
                return {"error": "Invoice parser agent not available"}
            
            print(f"[Orchestrator] Parsing invoice document of type: {file_type}")
            result = await agent.parse_invoice(file_content, file_type)
            
            return result
            
        except Exception as e:
            print(f"[Orchestrator] Invoice parsing error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _get_invoice_parser_agent(self) -> InvoiceParserAgent:
        """Get configured invoice parser agent."""
        config = self.manager.get_active_config()
        return InvoiceParserAgent(model=config.get("model"), api_key=config.get("api_key"))

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


