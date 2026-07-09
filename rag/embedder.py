"""Local embedding provider."""
import hashlib
import math
from functools import lru_cache

from config import get_settings


class LocalEmbedder:
    def __init__(self) -> None:
        self.dimension = 384
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(get_settings().embedding_model_name)
        except Exception:
            self._model = False
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._load_model()
        if model:
            vector = model.encode(text, normalize_embeddings=True).tolist()
            return [float(value) for value in vector]
        return self._hash_embedding(text)

    def _hash_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in (text or "").lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimension
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 8) for value in vector]


@lru_cache
def get_embedder() -> LocalEmbedder:
    return LocalEmbedder()
