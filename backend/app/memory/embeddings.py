from functools import lru_cache

from fastembed import TextEmbedding
import numpy as np

from backend.app.core.config import get_settings


class LocalEmbeddingService:
    """Semantic embeddings through FastEmbed library."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)
        self.dimensions = self._detect_dimensions(model_name)

    def embed(self, text: str) -> list[float]:
        embedding = next(self.model.embed([text]))
        return np.asarray(embedding, dtype=float).tolist()

    def _detect_dimensions(self, model_name: str) -> int:
        for model in TextEmbedding.list_supported_models():
            if model.get("model") == model_name and model.get("dim"):
                return int(model["dim"])
        return len(self.embed("dimension probe"))


# SentenceTransformers based
# It works, but it pulls the PyTorch/Transformers and makes Docker builds
# much slower for this app.
#
# from sentence_transformers import SentenceTransformer
#
# class SentenceTransformerEmbeddingService:
#     """Semantic embeddings via all-MiniLM-L6-v2."""
#
#     def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
#         self.model = SentenceTransformer(model_name)
#         self.dimensions = self.model.get_sentence_embedding_dimension()
#
#     def embed(self, text: str) -> list[float]:
#         return self.model.encode(text, normalize_embeddings=True).tolist()


@lru_cache
def get_embedding_service(model_name: str | None = None) -> LocalEmbeddingService:
    settings = get_settings()
    return LocalEmbeddingService(model_name or settings.embedding_model_name)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0
    left_vector = np.asarray(left, dtype=float)
    right_vector = np.asarray(right, dtype=float)
    if left_vector.shape != right_vector.shape:
        return 0
    left_norm = np.linalg.norm(left_vector)
    right_norm = np.linalg.norm(right_vector)
    if left_norm == 0 or right_norm == 0:
        return 0
    return float(np.dot(left_vector, right_vector) / (left_norm * right_norm))


# initilaize embeding download.
embedding = get_embedding_service()
