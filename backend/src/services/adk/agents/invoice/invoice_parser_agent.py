"""
Invoice Parser Agent - Extracts structured data from invoices via ADK multimodal.

Uses Gemini's vision capabilities to parse PDF/image invoices and extract
vendor info, line items, and financial totals.
"""
from typing import Optional, Dict, Any
from pathlib import Path
import os
import json

# Conditional ADK imports
try:
    from google.adk.agents import LlmAgent
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    LlmAgent = None
    types = None
    ADK_AVAILABLE = False


def load_prompt(filename: str) -> str:
    """Load a prompt from the prompts directory."""
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_path = prompts_dir / filename
    if prompt_path.exists():
        return prompt_path.read_text()
    return ""


class InvoiceParserAgent:
    """
    Agent that parses invoice documents using multimodal AI.
    Supports PDF and image files (PNG, JPG, JPEG).
    """
    
    def __init__(self, model: str = "gemini-2.0-flash", api_key: Optional[str] = None, instruction_file: str = "invoice_extraction.md"):
        self.model = model
        self.api_key = api_key
        self.instruction_file = instruction_file
        self._agent = None
        
        if self.api_key:
            os.environ["GOOGLE_API_KEY"] = self.api_key
            
        self._init_agent()
        
    def _init_agent(self):
        """Initialize the LLM agent."""
        if not ADK_AVAILABLE:
            print("[InvoiceParserAgent] ADK not available")
            return
            
        try:
            instruction = load_prompt(self.instruction_file)
            
            self._agent = LlmAgent(
                name="invoice_parser",
                model=self.model,
                instruction=instruction,
                description="Extracts structured data from invoice documents using vision.",
                output_key="invoice_extraction_result"
            )
            print(f"[InvoiceParserAgent] Agent initialized with model: {self.model}")
        except Exception as e:
            print(f"[InvoiceParserAgent] Init failed: {e}")
            import traceback
            traceback.print_exc()
            self._agent = None
            
    @property
    def adk_agent(self):
        return self._agent
    
    @property
    def is_available(self):
        return ADK_AVAILABLE and self._agent is not None

    async def parse_invoice(self, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """
        Parse an invoice document and extract structured data.
        
        Args:
            file_content: Raw bytes of the file
            file_type: MIME type (e.g., 'application/pdf', 'image/png')
            
        Returns:
            Dict with extracted invoice data or error
        """
        if not self.is_available:
            return {"error": "Invoice parser agent not available"}
        
        try:
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            import uuid
            
            # Create session
            session_service = InMemorySessionService()
            session_id = f"invoice_{uuid.uuid4().hex[:8]}"
            await session_service.create_session(
                app_name="fulcrum_invoice",
                user_id="system",
                session_id=session_id
            )
            
            # Build content parts based on file type
            parts = []
            
            if file_type == "application/pdf":
                # For PDF, encode as inline data
                parts.append(types.Part.from_bytes(
                    data=file_content,
                    mime_type="application/pdf"
                ))
            elif file_type.startswith("image/"):
                # For images, use inline data
                parts.append(types.Part.from_bytes(
                    data=file_content,
                    mime_type=file_type
                ))
            else:
                # For text/HTML, decode and send as text
                text_content = file_content.decode("utf-8", errors="ignore")
                parts.append(types.Part.from_text(text=f"Parse this invoice document:\n\n{text_content}"))
            
            # Add instruction
            parts.append(types.Part.from_text(
                text="Extract all invoice information from this document. Return ONLY valid JSON."
            ))
            
            user_content = types.Content(role="user", parts=parts)
            
            runner = Runner(
                agent=self._agent,
                session_service=session_service,
                app_name="fulcrum_invoice"
            )
            
            print(f"[InvoiceParserAgent] Processing document of type: {file_type}")
            
            # Run agent
            async for event in runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=user_content
            ):
                pass
            
            # Retrieve result from session state
            session = await session_service.get_session(
                app_name="fulcrum_invoice",
                user_id="system",
                session_id=session_id
            )
            
            result_text = session.state.get("invoice_extraction_result", "{}")
            
            # Parse JSON result
            return self._parse_json_response(result_text)
            
        except Exception as e:
            print(f"[InvoiceParserAgent] Parse error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def _parse_json_response(self, result_text: str) -> Dict[str, Any]:
        """Parse the JSON response from the LLM."""
        try:
            if isinstance(result_text, dict):
                return result_text
            
            clean = result_text.strip()
            
            # Remove markdown code block wrappers
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            
            return json.loads(clean.strip())
        except json.JSONDecodeError as e:
            print(f"[InvoiceParserAgent] JSON parse error: {e}")
            return {
                "error": "Failed to parse AI response as JSON",
                "raw_response": result_text[:500] if result_text else ""
            }
