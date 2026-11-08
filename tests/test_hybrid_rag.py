"""Comprehensive automated test suite for Phase 1: Local Multilingual Embeddings & Hybrid RAG."""
import math
import numpy as np
import pytest

from backend.app.rag.embed import (
    DeterministicSubwordEmbeddingProvider,
    LocalSentenceTransformerEmbeddingProvider,
    get_embedding_provider,
)
from backend.app.rag.retrieve import (
    RetrievedPassage,
    compute_bm25_scores,
    reciprocal_rank_fusion,
    tokenize_ethiopian_text,
)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    a = np.array(v1)
    b = np.array(v2)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


@pytest.mark.asyncio
async def test_deterministic_embedding_no_randomness():
    """Verify Rule 9: Embedding is 100% deterministic and produces identical vectors for identical text."""
    provider = DeterministicSubwordEmbeddingProvider(dimension=768)
    
    text = "ጤፍ ላይ ቢጫ ቅጠል እና የውሃ መተኛት"
    vec1 = await provider.embed_query(text)
    vec2 = await provider.embed_query(text)
    
    assert len(vec1) == 768
    assert len(vec2) == 768
    assert vec1 == vec2, "Vectors for identical text must be strictly identical (no random hash)"
    assert any(x != 0.0 for x in vec1), "Embedding vector must not be all zeros"
    
    # Check unit normalization
    norm = np.linalg.norm(np.array(vec1))
    assert math.isclose(norm, 1.0, rel_tol=1e-4)


@pytest.mark.asyncio
async def test_amharic_morphological_root_similarity():
    """Verify that morphologically related Amharic terms produce positive cosine alignment."""
    provider = DeterministicSubwordEmbeddingProvider(dimension=768)
    
    v_teff = await provider.embed_query("ጤፍ")
    v_yeteff = await provider.embed_query("የጤፍ ምርት")
    v_unrelated = await provider.embed_query("ኮምፒውተር ፕሮግራሚንግ")
    
    sim_related = cosine_similarity(v_teff, v_yeteff)
    sim_unrelated = cosine_similarity(v_teff, v_unrelated)
    
    assert sim_related > sim_unrelated, (
        f"Related Amharic terms ({sim_related:.3f}) must have higher similarity than unrelated ({sim_unrelated:.3f})"
    )


def test_ethiopian_text_tokenization():
    """Verify tokenization preserves both Ge'ez script and Latin words."""
    sample = "ጤፍ Teff በሽታ (Rust) በወይና ደጋ 1500m"
    tokens = tokenize_ethiopian_text(sample)
    
    assert "ጤፍ" in tokens
    assert "teff" in tokens
    assert "በሽታ" in tokens
    assert "rust" in tokens
    assert "ደጋ" in tokens


def test_bm25_exact_keyword_retrieval():
    """Verify BM25 strongly ranks exact agricultural term matches."""
    query = ["ኩትክዋቶ", "አረም"]
    
    doc1 = ["የጤፍ", "አረም", "መከላከያ", "ዘዴ", "ኩትክዋቶ", "ማድረግ"]
    doc2 = ["ስንዴ", "ላይ", "ዋግ", "በሽታ", "መከላከያ"]
    doc3 = ["የበቆሎ", "ምርት", "ማሳደጊያ", "ማዳበሪያ", "አጠቃቀም"]
    
    docs = [doc1, doc2, doc3]
    scores = compute_bm25_scores(query, docs)
    
    assert len(scores) == 3
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]
    assert scores[0] > 0.0
    assert scores[1] == 0.0


def test_reciprocal_rank_fusion_scoring():
    """Verify RRF balances dense and sparse rankings using TREC k=60."""
    dense_ranks = {"doc_a": 1, "doc_b": 2, "doc_c": 3}
    bm25_ranks = {"doc_b": 1, "doc_c": 2, "doc_a": 3}
    
    rrf = reciprocal_rank_fusion(dense_ranks, bm25_ranks, k=60, dense_weight=1.0, bm25_weight=0.8)
    
    # doc_a: 1.0/(60+1) + 0.8/(60+3) = 0.01639 + 0.01269 = 0.02908
    # doc_b: 1.0/(60+2) + 0.8/(60+1) = 0.01612 + 0.01311 = 0.02923
    assert rrf["doc_b"] > rrf["doc_a"]
    assert all(score > 0 for score in rrf.values())


@pytest.mark.asyncio
async def test_local_provider_factory(monkeypatch):
    """Verify provider factory returns appropriate local embedding provider without network calls."""
    from backend.app.config import settings

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "local")
    provider = get_embedding_provider()
    assert provider is not None
    assert provider.dimension > 0
    vec = await provider.embed_query("ባህር ዳር")
    assert len(vec) == provider.dimension
    assert any(x != 0.0 for x in vec)
