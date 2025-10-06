"""
Celery tasks for the Fulcrum application.

This module contains the definitions for background tasks that are executed
asynchronously by the Celery worker.
"""
from .celery_worker import celery_app
from src.database import SessionLocal
from src.crud import crud_product
from src.services.dummy_ai_service import ai_service

@celery_app.task
def generate_product_embedding(product_id: int):
    """
    Generates and saves a vector embedding for a product using the AI service.
    """
    db = SessionLocal()
    try:
        product = crud_product.product.get(db, id=product_id)
        if not product:
            print(f"Product with ID {product_id} not found.")
            return

        # In a real app, you might combine more fields
        text_to_embed = f"{product.name} {product.description}"
        embedding = ai_service.generate_embedding(text_to_embed)

        # Update the product with the new embedding
        crud_product.product.update(db, db_obj=product, obj_in={"embedding": embedding})
        print(f"Successfully generated and saved embedding for product ID: {product_id}")
    finally:
        db.close()

    return {"product_id": product_id, "status": "success"}
