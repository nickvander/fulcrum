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

    def identify_from_image(self, image_bytes: bytes) -> str:
        """
        Returns a dummy identification string.
        """
        return "dummy_identification"

ai_service = DummyAIService()
