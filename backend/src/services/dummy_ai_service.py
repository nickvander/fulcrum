import numpy as np
from src.services.base import AIService

class DummyAIService(AIService):
    """
    A dummy AI service that generates random embeddings for testing.
    """
    def generate_embedding(self, text: str) -> list[float]:
        """
        Generates a random 384-dimensional embedding.
        The dimensionality is chosen to match common embedding models.
        """
        # The content of the text is ignored, we just return a random vector.
        # A real implementation would call an AI model here.
        return np.random.rand(384).tolist()

    def identify_product_from_image(self, image_url: str) -> dict:
        """
        Returns a dummy product identification dictionary based on a mock SKU.
        The image_url is ignored in this dummy implementation.
        """
        # In a real service, you would fetch the image from the URL and send
        # it to an AI model. Here, we just return a fixed dictionary.
        return {
            "name": "AI-Identified Widget",
            "description": "A high-quality widget identified from an image.",
            "sku": "AI-SKU-123",
        }

ai_service = DummyAIService()
