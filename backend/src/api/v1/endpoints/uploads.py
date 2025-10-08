"""
API endpoints for handling file uploads.
"""
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file and save it to the server.
    Returns the path to the saved file.
    """
    try:
        # Ensure the filename is secure
        if ".." in file.filename or "/" in file.filename:
            raise HTTPException(status_code=400, detail="Invalid filename.")

        file_path = UPLOADS_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {"file_path": str(file_path)}
    finally:
        file.file.close()
