"""Vector store and PostgreSQL pgvector ingestion."""
import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.database.models import AgriculturalDocument, KnowledgeChunk
    from app.rag.embed import get_embedding_provider
    from app.rag.ingest import IngestedDocument
except ImportError:
    from backend.app.database.models import AgriculturalDocument, KnowledgeChunk
    from backend.app.rag.embed import get_embedding_provider
    from backend.app.rag.ingest import IngestedDocument

logger = logging.getLogger("hello_farmer.rag.store")


async def store_ingested_document(
    doc: IngestedDocument,
    session: AsyncSession,
) -> int:
    """Store document metadata and embedded knowledge chunks in pgvector."""
    # Check if document already exists
    stmt = select(AgriculturalDocument).where(AgriculturalDocument.id == doc.document_id)
    result = await session.execute(stmt)
    existing_doc = result.scalar_one_or_none()

    if existing_doc:
        # Delete old chunks to allow re-ingestion
        await session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == existing_doc.id)
        )
        existing_doc.title = doc.title
        existing_doc.publisher = doc.publisher
        existing_doc.publication_year = doc.publication_year
        existing_doc.source_tier = doc.source_tier
        existing_doc.language = doc.language
        existing_doc.file_path = doc.file_path
        db_doc = existing_doc
    else:
        db_doc = AgriculturalDocument(
            id=doc.document_id,
            title=doc.title,
            publisher=doc.publisher,
            publication_year=doc.publication_year,
            source_tier=doc.source_tier,
            language=doc.language,
            file_path=doc.file_path,
        )
        session.add(db_doc)

    await session.flush()

    if not doc.chunks:
        await session.commit()
        return 0

    # Generate embeddings
    embedder = get_embedding_provider()
    chunk_texts = [c.content for c in doc.chunks]
    embeddings = await embedder.embed_texts(chunk_texts)

    chunks_to_add = []
    for i, chunk in enumerate(doc.chunks):
        vec = embeddings[i] if i < len(embeddings) else None
        k_chunk = KnowledgeChunk(
            document_id=db_doc.id,
            content=chunk.content,
            embedding=vec,
            crop=chunk.crop,
            region=doc.region,
            topic=chunk.topic,
            source_tier=doc.source_tier,
            page_number=chunk.page_number,
        )
        chunks_to_add.append(k_chunk)

    session.add_all(chunks_to_add)
    await session.commit()
    logger.info(f"Ingested '{doc.title}' with {len(chunks_to_add)} chunks into pgvector.")
    return len(chunks_to_add)
