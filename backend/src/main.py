from fastapi import FastAPI
from .api import products, suppliers

app = FastAPI(title="Fulcrum API")

app.include_router(products.router)
app.include_router(suppliers.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Fulcrum API"}
