"""
API endpoints for AI-related tasks.
"""
import shutil
import tempfile
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
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
