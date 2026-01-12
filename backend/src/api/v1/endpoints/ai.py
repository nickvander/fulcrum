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
from src.services.adk.manager import ADKManager
from src.services.adk.orchestrator import AgentOrchestrator

router = APIRouter()

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
        # 2. Initialize ADK Manager & Orchestrator
        adk_manager = ADKManager(db)
        orchestrator = AgentOrchestrator(adk_manager)
        
        # 3. Process with Vision Agent (via Orchestrator)
        result = await orchestrator.process_product_image(tmp_path)
        
        # 4. Format Response
        return ImageIdentificationResponse(**result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
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
        # Initialize ADK Manager & Orchestrator
        adk_manager = ADKManager(db)
        orchestrator = AgentOrchestrator(adk_manager)
        
        # Generate description via orchestrator
        result = await orchestrator.generate_product_description(
            product_name=request.product_name,
            context=request.context,
            tone=request.tone,
            length=request.length
        )
        
        # Format Response
        if "error" in result:
            return DescriptionGenerationResponse(error=result["error"])
        
        return DescriptionGenerationResponse(
            description=result.get("description"),
            seo_keywords=result.get("seo_keywords", []),
            tone_used=result.get("tone_used")
        )

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
        
        # 4. Initialize ADK Manager & Orchestrator
        adk_manager = ADKManager(db)
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

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
