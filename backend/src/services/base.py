from abc import ABC, abstractmethod

class AIService(ABC):
    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def identify_product_from_image(self, image_url: str) -> dict:
        """Analyzes an image from a URL and returns structured product data."""
        pass

class FileStorageService(ABC):
    @abstractmethod
    def generate_upload_url(self, file_name: str) -> str:
        pass

    @abstractmethod
    def upload_file(self, file_bytes: bytes, file_name: str) -> str:
        pass
