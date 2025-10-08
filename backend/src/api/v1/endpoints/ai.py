"""
API endpoints for AI-related tasks.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional

from src.api.dependencies import get_ai_service
from src.services.base import AIService

router = APIRouter()

class ImageIdentificationRequest(BaseModel):
    image_url: HttpUrl

class ImageIdentificationResponse(BaseModel):
    name: str
    description: str
    sku: Optional[str] = None

@router.post("/identify-from-image", response_model=ImageIdentificationResponse)
def identify_from_image(
    request: ImageIdentificationRequest,
    ai_service: AIService = Depends(get_ai_service),
):
    """
    Analyze an image from a URL and return identified product information.
    """
    try:
        product_info = ai_service.identify_product_from_image(str(request.image_url))
        if not product_info:
            raise HTTPException(status_code=404, detail="Could not identify product from image.")
        return ImageIdentificationResponse(**product_info)
    except Exception as e:
        # In a real app, you'd have more specific error handling and logging
        raise HTTPException(status_code=500, detail=str(e))
