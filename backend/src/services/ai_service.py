from typing import Protocol

class AIService(Protocol):
    def generate_embedding(self, text: str) -> list[float]:
        ...

class SentenceTransformerService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Defer the import until the class is actually used
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            raise ImportError("sentence-transformers is required for this service but is not installed.")

    def generate_embedding(self, text: str) -> list[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()

class DummyAIService:
    def generate_embedding(self, text: str) -> list[float]:
        print(f"Warning: Using DummyAIService. Generating dummy embedding for: {text}")
        return [0.0] * 384

def get_ai_service() -> AIService:
    # In a real application, you might use a configuration setting
    # to switch between the real and dummy service.
    # For now, we'll default to the real one if the model is available,
    # otherwise fall back to the dummy.
    try:
        return SentenceTransformerService()
    except (ImportError, Exception) as e:
        print(f"Could not load SentenceTransformer model, falling back to dummy AI service. Error: {e}")
        return DummyAIService()
