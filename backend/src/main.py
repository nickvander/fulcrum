from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.api.v1.api import api_router

app = FastAPI(title="Fulcrum API")

# Mount the uploads directory to serve static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Fulcrum API"}
