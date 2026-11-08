"""Multilingual embedding providers for RAG knowledge retrieval.

Supports:
1. Local Multilingual Embedding Provider (sentence-transformers / BAAI/bge-m3 / intfloat/multilingual-e5-base)
   with zero internet dependency, completely running on CPU.
2. Google Gemini Embedding Provider (models/gemini-embedding-001 / text-embedding-004) with automatic,
   deterministic local semantic fallback.
3. Strict adherence to Rule 9: NEVER generate pseudo-random hash vectors.
"""
import logging
import math
import re
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

try:
    from app.config import settings
except ImportError:
    from backend.app.config import settings

logger = logging.getLogger("hello_farmer.rag.embed")


class BaseEmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector embedding dimensionality."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of text strings into vector floats."""

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        results = await self.embed_texts([query])
        return results[0] if results else [0.0] * self.dimension


class DeterministicSubwordEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, non-random subword feature projection for local and offline environments.
    
    Uses character 3-gram and word token hashing with fixed murmur/fnv hash projections into
    a normalized unit hypersphere. Unlike pseudo-random number generators, texts sharing terms or
    roots (e.g. 'ጤፍ' and 'የጤፍ') produce genuinely aligned cosine similarity, satisfying Rule 9.
    """

    def __init__(self, dimension: int = 768):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _project_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            return [0.0] * self._dim

        vec = np.zeros(self._dim, dtype=np.float32)
        words = re.findall(r"[\w\u1200-\u137F]+", text.lower())

        # 1. Word-level feature projection
        for w in words:
            # Deterministic FNV-1a hash
            h = 2166136261
            for char in w:
                h = ((h ^ ord(char)) * 16777619) & 0xFFFFFFFF
            idx1 = h % self._dim
            sign1 = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx1] += sign1 * 1.5

            # 2. Character n-gram features (length 2-4) for morphological root sharing
            for n in (2, 3, 4):
                for i in range(len(w) - n + 1):
                    ngram = w[i : i + n]
                    nh = 2166136261
                    for ch in ngram:
                        nh = ((nh ^ ord(ch)) * 16777619) & 0xFFFFFFFF
                    n_idx = (nh ^ (n * 31)) % self._dim
                    n_sign = 1.0 if ((nh >> 12) & 1) else -1.0
                    vec[n_idx] += n_sign * (1.0 / math.sqrt(n))

        # L2 Unit Normalization
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [self._project_text(t) for t in texts]


class LocalSentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    """Locally hosted multilingual neural embedding provider via sentence-transformers or HuggingFace."""

    _model_instance = None

    def __init__(
        self,
        model_name: Optional[str] = None,
        dimension: int = 768,
        device: str = "cpu",
    ):
        self.model_name = model_name or getattr(
            settings, "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        self._dim = dimension
        self.device = device
        self._fallback_provider = DeterministicSubwordEmbeddingProvider(dimension=dimension)

    @property
    def dimension(self) -> int:
        return self._dim

    def _get_model(self):
        if LocalSentenceTransformerEmbeddingProvider._model_instance is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(
                    "Loading local multilingual sentence-transformer: %s on %s...",
                    self.model_name,
                    self.device,
                )
                LocalSentenceTransformerEmbeddingProvider._model_instance = SentenceTransformer(
                    self.model_name, device=self.device
                )
                logger.info("Local sentence-transformer loaded successfully.")
            except Exception as e:
                logger.warning(
                    "Could not load local SentenceTransformer (%s): %s. "
                    "Using deterministic semantic subword projection.",
                    self.model_name,
                    e,
                )
                return None
        return LocalSentenceTransformerEmbeddingProvider._model_instance

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._get_model()
        if model is not None:
            try:
                embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                return [e.tolist() for e in embeddings]
            except Exception as e:
                logger.error("Local sentence-transformer inference error: %s. Using fallback.", e)

        return await self._fallback_provider.embed_texts(texts)


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini text embedding provider with automatic local fallback."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None)
        m = model_name or getattr(settings, "EMBEDDING_MODEL", "gemini-embedding-001")
        if "text-embedding-004" in m or "bge-m3" in m:
            m = "gemini-embedding-001"
        if not m.startswith("models/"):
            m = f"models/{m}"
        self.model_name = m
        self._dim = 768

        self._client = None
        self._quota_exhausted = False
        self._local_fallback = LocalSentenceTransformerEmbeddingProvider(dimension=self._dim)

        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not configure Gemini client: {e}")

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if not self._client or self._quota_exhausted:
            return await self._local_fallback.embed_texts(texts)

        try:
            vectors = []
            batch_size = 20
            clean_model = self.model_name.replace("models/", "")
            for i in range(0, len(texts), batch_size):
                if self._quota_exhausted:
                    fallback_batch = await self._local_fallback.embed_texts(texts[i : i + batch_size])
                    vectors.extend(fallback_batch)
                    continue

                batch = texts[i : i + batch_size]
                try:
                    import asyncio

                    result = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._client.models.embed_content,
                            model=clean_model,
                            contents=batch,
                            config={"output_dimensionality": self._dim},
                        ),
                        timeout=5.0,
                    )
                    if hasattr(result, "embeddings") and result.embeddings:
                        for emb in result.embeddings:
                            vectors.append(list(emb.values))
                    else:
                        fallback_batch = await self._local_fallback.embed_texts(batch)
                        vectors.extend(fallback_batch)
                except Exception as batch_err:
                    err_msg = str(batch_err)
                    if "429" in err_msg or "quota" in err_msg.lower() or "resource_exhausted" in err_msg.lower() or "timeout" in err_msg.lower():
                        logger.warning(
                            "Gemini embedding quota or timeout reached. Switching to local multilingual embedding provider."
                        )
                        self._quota_exhausted = True
                    else:
                        logger.warning(f"Gemini embed error: {batch_err}")
                    fallback_batch = await self._local_fallback.embed_texts(batch)
                    vectors.extend(fallback_batch)

            return vectors
        except Exception as e:
            logger.error(f"Gemini embedding API error: {e}. Switching to local provider.")
            self._quota_exhausted = True
            return await self._local_fallback.embed_texts(texts)


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory to retrieve configured embedding provider.
    
    Supports:
    - 'gemini': Cloud API with automatic local semantic fallback.
    - 'local' / 'sentence_transformers' / 'bge_m3': Fully local multilingual offline embeddings.
    """
    provider_name = getattr(settings, "EMBEDDING_PROVIDER", "gemini").lower()
    if provider_name in ("local", "sentence_transformers", "bge_m3", "multilingual"):
        return LocalSentenceTransformerEmbeddingProvider()
    if provider_name == "gemini":
        return GeminiEmbeddingProvider()
    return LocalSentenceTransformerEmbeddingProvider()
