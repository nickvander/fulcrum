from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Optional, List
from pydantic import BaseModel

from src.api import dependencies as deps
from src.models.product import Product
from src.models.marketing import CampaignEvent
from src.services.adk.agents.marketing.root_agent import MarketingRootAgent
from src.config import settings

router = APIRouter()


# --- Tone Presets ---

class TonePreset(BaseModel):
    id: str
    name: str
    prompt: str
    description: str


def _load_prompt_file(filename: str) -> str:
    """Load prompt content from a .md file."""
    from pathlib import Path
    prompts_dir = Path(__file__).parent.parent / "services" / "adk" / "agents" / "marketing" / "prompts"
    filepath = prompts_dir / filename
    if filepath.exists():
        return filepath.read_text()
    return ""


def _load_tone_prompt(tone_id: str) -> str:
    """Load tone-specific prompt from tones/{tone_id}.md"""
    return _load_prompt_file(f"tones/{tone_id}.md")


def _load_channel_guidelines(channel: str) -> str:
    """Load channel-specific guidelines from channels/{channel}.md"""
    channel_lower = channel.lower().replace("/", "").replace(" ", "")
    if channel_lower in ["twitter", "x", "twitterx"]:
        channel_lower = "twitter"
    return _load_prompt_file(f"channels/{channel_lower}.md")


# Default tone presets - prompts loaded from .md files
TONE_PRESETS: List[TonePreset] = [
    TonePreset(
        id="professional",
        name="Professional",
        prompt=_load_tone_prompt("professional") or "Write a professional, polished social media post that highlights the key features and value proposition of this product. Use clear, confident language suitable for business audiences.",
        description="Formal and polished for business audiences"
    ),
    TonePreset(
        id="casual",
        name="Casual",
        prompt=_load_tone_prompt("casual") or "Write a friendly, conversational social media post about this product. Keep it relaxed and approachable, like you're telling a friend about something cool you discovered.",
        description="Friendly and approachable"
    ),
    TonePreset(
        id="viral",
        name="Viral / Hype",
        prompt=_load_tone_prompt("viral") or "Write an attention-grabbing, viral-style social media post that creates excitement and FOMO. Use punchy language, emojis, and trending phrases to maximize engagement and shares.",
        description="Attention-grabbing with high engagement"
    ),
    TonePreset(
        id="luxury",
        name="Luxury",
        prompt=_load_tone_prompt("luxury") or "Write an elegant, sophisticated social media post that emphasizes exclusivity, premium quality, and refined taste. Use aspirational language that appeals to discerning customers.",
        description="Elegant and sophisticated"
    ),
    TonePreset(
        id="custom",
        name="Custom",
        prompt="",
        description="Write your own prompt"
    ),
]


# Channel guidelines endpoint
class ChannelGuidelines(BaseModel):
    channel: str
    guidelines: str


@router.get("/channel-guidelines/{channel}")
async def get_channel_guidelines(channel: str) -> ChannelGuidelines:
    """Get channel-specific posting guidelines."""
    guidelines = _load_channel_guidelines(channel)
    return ChannelGuidelines(channel=channel, guidelines=guidelines)


@router.get("/tone-presets", response_model=List[TonePreset])
async def get_tone_presets() -> List[TonePreset]:
    """Get available tone presets for AI content generation."""
    return TONE_PRESETS


# --- Content Generation ---

class ContentGenerationRequest(BaseModel):
    product_id: int
    platform: str = "Twitter"  # Twitter, Instagram
    tone: str = "Professional"
    custom_prompt: Optional[str] = None  # User-edited prompt
    generate_image: bool = True
    campaign_id: Optional[int] = None

class ContentGenerationResponse(BaseModel):
    research: dict
    content: dict
    image_concept: dict
    generated_image_url: Optional[str] = None
    event_id: Optional[int] = None

@router.post("/generate-content", response_model=ContentGenerationResponse)
async def generate_marketing_content(
    request: ContentGenerationRequest,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate marketing content using AI Agents.
    """
    # 1. Get Product
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Initialize Agent
    # Try fetching from DB settings first
    from src.crud.crud_store_settings import store_settings
    from src.core.encryption import encryption_service
    
    settings_obj = store_settings.get_settings(db)
    api_key = None
    
    if settings_obj.ai_google_api_key:
        try:
            api_key = encryption_service.decrypt(settings_obj.ai_google_api_key)
        except Exception as e:
            print(f"Failed to decrypt API key from DB: {e}")
            
    # Fallback to env
    if not api_key:
        api_key = settings.GEMINI_API_KEY if hasattr(settings, "GEMINI_API_KEY") else None
    
    agent = MarketingRootAgent(api_key=api_key)
    if not agent.is_available:
        # If no key found, give a specific error
        if not api_key:
            raise HTTPException(status_code=503, detail="AI Service unavailable: Valid API Key not found in Store Settings or Environment.")
        else:
            raise HTTPException(status_code=503, detail="AI Service unavailable (ADK missing?)")

    # 3. Run Generation Pipeline
    # Get product image URL if available
    product_image_url = None
    if product.primary_image:
        product_image_url = product.primary_image.image_path
    elif product.images and len(product.images) > 0:
        product_image_url = product.images[0].image_path
    
    try:
        result = await agent.generate_campaign(
            product_name=product.name,
            product_description=product.description or "",
            platform=request.platform,
            generate_image=request.generate_image,
            product_image_url=product_image_url
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        # 4. Save as Draft Event
        # Map properties
        content_data = result.get("content", {})
        post_text = content_data.get("content", "")
        
        event = CampaignEvent(
            campaign_id=request.campaign_id,
            name=f"AI Generated {request.platform} Post",
            channel_type=request.platform.lower(), # Map to rough channel type
            status="draft",
            content_body=post_text,
            content_image_url=result.get("generated_image_url"),
            content_json=result, # Store full AI metadata
        )
        db.add(event)
        
        # Link product
        event.products.append(product)
        
        db.commit()
        db.refresh(event)
        
        # Add event_id to response
        result["event_id"] = event.id
        
        return result
        
    except Exception as e:
        print(f"Error generating content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
