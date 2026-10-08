"""Agricultural Knowledge Base Retrieval Engine.

Implements:
- Vector similarity search via PostgreSQL pgvector cosine distance.
- Cross-lingual retrieval (Amharic / Afaan Oromo matching English & vernacular chunks).
- Similarity threshold filtering (below threshold -> question 'not covered').
- Source tier attribution (Tiers 1, 2, 3, and placeholder).
"""
import logging

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.config import settings
    from app.database.models import AgriculturalDocument, KnowledgeChunk
    from app.rag.embed import get_embedding_provider
except ImportError:
    from backend.app.config import settings
    from backend.app.database.models import AgriculturalDocument, KnowledgeChunk
    from backend.app.rag.embed import get_embedding_provider

logger = logging.getLogger("hello_farmer.rag.retrieve")


class RetrievedPassage(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    source_tier: int
    score: float  # Cosine similarity score (0.0 to 1.0)
    crop: str | None = None
    topic: str | None = None
    page_number: int | None = None
    is_placeholder: bool = False


async def retrieve_passages(
    query: str,
    session: AsyncSession,
    top_k: int = 4,
    similarity_threshold: float | None = None,
    crop_filter: str | None = None,
) -> list[RetrievedPassage]:
    """Retrieve top-k relevant knowledge passages from pgvector.

    Args:
        query: Caller or user question text.
        session: Database async session.
        top_k: Maximum number of chunks to return.
        similarity_threshold: Minimum cosine similarity score (defaults to config: 0.65).
        crop_filter: Optional crop filter (e.g. 'teff', 'wheat', 'maize').

    Returns:
        List of RetrievedPassage objects meeting the similarity threshold.
    """
    if not query or not query.strip():
        return []

    threshold = similarity_threshold if similarity_threshold is not None else getattr(
        settings, "SIMILARITY_THRESHOLD", 0.65
    )

    embedder = get_embedding_provider()
    query_vector = await embedder.embed_query(query)

    # Use pgvector cosine distance: <=> operator
    # Cosine distance = 1 - cosine_similarity. So cosine_similarity = 1 - distance.
    cosine_dist = KnowledgeChunk.embedding.cosine_distance(query_vector)

    stmt = (
        select(
            KnowledgeChunk,
            AgriculturalDocument.title.label("doc_title"),
            AgriculturalDocument.source_tier.label("doc_tier"),
            (1.0 - cosine_dist).label("similarity_score"),
        )
        .join(AgriculturalDocument, KnowledgeChunk.document_id == AgriculturalDocument.id)
        .where(KnowledgeChunk.embedding.is_not(None))
    )

    if crop_filter:
        stmt = stmt.where(KnowledgeChunk.crop == crop_filter)

    # Order by similarity descending (distance ascending)
    stmt = stmt.order_by(cosine_dist.asc()).limit(top_k * 2)

    result = await session.execute(stmt)
    rows = result.all()

    passages: list[RetrievedPassage] = []
    for chunk, doc_title, doc_tier, similarity_score in rows:
        score = float(similarity_score) if similarity_score is not None else 0.0

        # Filter below threshold
        if score < threshold:
            continue

        is_ph = (doc_tier == 0 or "placeholder" in (doc_title or "").lower())
        passages.append(
            RetrievedPassage(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=doc_title or "Agricultural Guide",
                content=chunk.content,
                source_tier=doc_tier,
                score=score,
                crop=chunk.crop,
                topic=chunk.topic,
                page_number=chunk.page_number,
                is_placeholder=is_ph,
            )
        )

        if len(passages) >= top_k:
            break

    logger.info(
        f"Retrieved {len(passages)} passages for query '{query[:30]}...' (Threshold: {threshold})"
    )
    return passages
