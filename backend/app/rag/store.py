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


async def persist_web_passages_to_rag(
    passages: list[dict],
    crop: str | None = None,
    language: str = "am",
) -> int:
    """Save live web search passages into PostgreSQL pgvector KnowledgeChunks for future reference and semantic retrieval."""
    if not passages:
        return 0

    try:
        try:
            from app.database.session import async_session_factory
        except ImportError:
            from backend.app.database.session import async_session_factory

        doc_id = "doc_web_search_knowledge_vault"
        async with async_session_factory() as session:
            # Ensure parent AgriculturalDocument exists
            stmt = select(AgriculturalDocument).where(AgriculturalDocument.id == doc_id)
            res = await session.execute(stmt)
            doc = res.scalar_one_or_none()
            if not doc:
                doc = AgriculturalDocument(
                    id=doc_id,
                    title="Live Agricultural Web Knowledge Vault",
                    publisher="Live Web Agronomy Search (EIAR/FAO/MoA Sources)",
                    publication_year=2026,
                    source_tier=1,
                    language=language,
                    file_path="web_search_cache",
                )
                session.add(doc)
                await session.flush()

            # Filter out chunks that already exist
            valid_passages = []
            for p in passages:
                text = p.get("text", "").strip()
                if not text or len(text) < 25:
                    continue
                dup_stmt = select(KnowledgeChunk.id).where(
                    KnowledgeChunk.document_id == doc_id,
                    KnowledgeChunk.content == text,
                ).limit(1)
                dup_res = await session.execute(dup_stmt)
                if not dup_res.scalar_one_or_none():
                    valid_passages.append(p)

            if not valid_passages:
                return 0

            embedder = get_embedding_provider()
            texts_to_embed = [p["text"].strip() for p in valid_passages]
            try:
                embeddings = await embedder.embed_texts(texts_to_embed)
            except Exception as e:
                logger.warning("Failed to embed web passages batch: %s", e)
                embeddings = [None] * len(texts_to_embed)

            import uuid
            chunks_to_add = []
            for i, p in enumerate(valid_passages):
                vec = embeddings[i] if i < len(embeddings) else None
                chunk = KnowledgeChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    content=p["text"].strip(),
                    embedding=vec,
                    crop=crop,
                    topic=p.get("title", "Agricultural Advisory"),
                    source_tier=1,
                )
                chunks_to_add.append(chunk)

            session.add_all(chunks_to_add)
            await session.commit()
            logger.info(f"Successfully saved {len(chunks_to_add)} live web search passages into RAG knowledge base for future queries.")
            return len(chunks_to_add)
    except Exception as e:
        logger.warning(f"Error persisting web passages to RAG: {e}")
        return 0

