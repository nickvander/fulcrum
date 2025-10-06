from fastapi import FastAPI
from .api import products

app = FastAPI(title="Fulcrum API")

app.include_router(products.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Fulcrum API"}
