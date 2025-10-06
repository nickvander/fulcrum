from fastapi import FastAPI
from src.api.v1.api import api_router

app = FastAPI(title="Fulcrum API")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Fulcrum API"}
