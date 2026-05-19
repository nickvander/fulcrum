"""
API endpoints for AI-related tasks.
"""
import shutil
import tempfile
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.core.errors import LocalizedHTTPException
from src.services.adk.manager import ADKManager
from src.services.adk.orchestrator import AgentOrchestrator

router = APIRouter()


class AICapabilities(BaseModel):
    """Per-workspace AI readiness, used by the frontend to gate AI UI controls.

    `ready` is the single predicate UI should branch on; `enabled` and
    `configured` are exposed only so the Settings screen can tell the user
    *which* gate is closed when buttons are hidden.
    """
    ready: bool = False
    enabled: bool = False
    configured: bool = False
    provider: Optional[str] = None


def _require_ai_ready(db: Session) -> ADKManager:
    """Return an ADKManager when AI is ready, otherwise raise a localized 400.

    Centralized so every AI endpoint refuses the same way; the frontend keys
    off the `apiErrors.ai.disabled` code to localize the message.
    """
    manager = ADKManager(db)
    if not manager.is_ready():
        raise LocalizedHTTPException(
            status_code=400,
            code="apiErrors.ai.disabled",
            detail=(
                "AI features are disabled. Enable AI and configure an API key "
                "for the active provider in Settings."
            ),
        )
    return manager


@router.get("/capabilities", response_model=AICapabilities)
def get_ai_capabilities(db: Session = Depends(get_db)) -> AICapabilities:
    """Tell the frontend whether AI-backed actions are available right now."""
    manager = ADKManager(db)
    settings = manager.settings
    enabled = bool(settings and settings.ai_enabled)
    provider = (settings.ai_provider if settings else None) or "google"
    configured = manager.is_configured(provider)
    return AICapabilities(
        ready=enabled and configured,
        enabled=enabled,
        configured=configured,
        provider=provider,
    )

class ImageIdentificationResponse(BaseModel):
    name: str = "Unknown"
    brand: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    error: Optional[str] = None
    exists: bool = False
    product_id: Optional[int] = None
    message: Optional[str] = None
    # AI Analysis Fields (preserved even if DB match found)
    ai_name: Optional[str] = None
    ai_brand: Optional[str] = None
    ai_description: Optional[str] = None


class DescriptionGenerationRequest(BaseModel):
    product_name: str
    context: Optional[str] = None
    tone: Optional[str] = None
    length: Optional[str] = None


class DescriptionGenerationResponse(BaseModel):
    description: Optional[str] = None
    seo_keywords: List[str] = []
    tone_used: Optional[str] = None
    error: Optional[str] = None


class ListingDescriptionRequest(BaseModel):
    """Request model for marketplace-specific listing generation."""
    product_id: int
    marketplace_name: str  # e.g., "amazon", "mercadolibre", "ebay"
    include_title: bool = True
    include_keywords: bool = True


class ListingDescriptionResponse(BaseModel):
    """Response with marketplace-optimized listing content."""
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = []
    marketplace: str = ""
    error: Optional[str] = None


@router.post("/identify-product", response_model=ImageIdentificationResponse)
async def identify_product(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Analyze an uploaded image and return identified product information.
    """
    # 1. Save Upload to Temp (Agent needs path)
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        adk_manager = _require_ai_ready(db)
        orchestrator = AgentOrchestrator(adk_manager)
        result = await orchestrator.process_product_image(tmp_path)
        return ImageIdentificationResponse(**result)

    except LocalizedHTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/generate-description", response_model=DescriptionGenerationResponse)
async def generate_description(
    request: DescriptionGenerationRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a marketing description for a product using AI.
    
    Uses the ADK DescriptionAgent to create compelling, SEO-friendly
    product descriptions based on the provided product name and context.
    """
    try:
        adk_manager = _require_ai_ready(db)
        orchestrator = AgentOrchestrator(adk_manager)

        result = await orchestrator.generate_product_description(
            product_name=request.product_name,
            context=request.context,
            tone=request.tone,
            length=request.length
        )

        if "error" in result:
            return DescriptionGenerationResponse(error=result["error"])

        return DescriptionGenerationResponse(
            description=result.get("description"),
            seo_keywords=result.get("seo_keywords", []),
            tone_used=result.get("tone_used")
        )

    except LocalizedHTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-listing-description", response_model=ListingDescriptionResponse)
async def generate_listing_description(
    request: ListingDescriptionRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a marketplace-optimized listing description for a product.
    
    This endpoint generates titles, descriptions, and keywords tailored
    for specific marketplaces like Amazon, MercadoLibre, or eBay.
    """
    from src.crud.crud_product import product as product_crud

    try:
        # Gate first — refuse cleanly before any DB lookups when AI is off.
        adk_manager = _require_ai_ready(db)

        # 1. Fetch product details
        product = product_crud.get(db, id=request.product_id)
        if not product:
            return ListingDescriptionResponse(
                error=f"Product with ID {request.product_id} not found",
                marketplace=request.marketplace_name
            )
        
        # 2. Build context from product data
        context_parts = [
            f"Product Name: {product.name}",
            f"Brand: {product.brand}" if product.brand else None,
            f"Category: {product.category}" if product.category else None,
            f"Current Description: {product.description}" if product.description else None,
            f"SKU: {product.sku}" if product.sku else None,
        ]
        context = "\n".join([p for p in context_parts if p])
        
        # 3. Determine tone based on marketplace
        marketplace = request.marketplace_name.lower()
        tone_map = {
            "amazon": "Professional and SEO-focused for Amazon shoppers",
            "mercadolibre": "Friendly and direct for Latin American buyers",
            "ebay": "Casual and deal-oriented for eBay users",
        }
        tone = tone_map.get(marketplace, "Professional")
        
        # 4. Initialize orchestrator (manager already verified ready above)
        orchestrator = AgentOrchestrator(adk_manager)

        # 5. Generate listing content via orchestrator
        result = await orchestrator.generate_product_description(
            product_name=product.name,
            context=f"Target Marketplace: {request.marketplace_name}\n{context}",
            tone=tone,
            length="medium"
        )
        
        # 6. Format Response
        if "error" in result:
            return ListingDescriptionResponse(
                error=result["error"],
                marketplace=request.marketplace_name
            )
        
        # Generate a title if requested
        title = None
        if request.include_title:
            # Use first sentence of description or product name + brand
            title = f"{product.name}"
            if product.brand:
                title = f"{product.brand} {title}"
        
        return ListingDescriptionResponse(
            title=title,
            description=result.get("description"),
            keywords=result.get("seo_keywords", []) if request.include_keywords else [],
            marketplace=request.marketplace_name
        )

    except LocalizedHTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
