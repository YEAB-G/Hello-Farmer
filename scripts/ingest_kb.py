"""CLI Script to ingest knowledge base documents into PostgreSQL pgvector."""
import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.config import settings
from backend.app.rag.ingest import parse_and_validate_document
from backend.app.rag.store import store_ingested_document


async def main():
    print("=" * 80)
    print("HELLO FARMER: KNOWLEDGE BASE INGESTION PIPELINE (PHASE 3)")
    print("=" * 80)

    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("knowledge_base/raw/MoA Guidelines")
    if not target_path.exists():
        target_path = Path("knowledge_base/raw")
    if not target_path.exists():
        print(f"Path {target_path} does not exist!")
        return

    if target_path.is_file():
        doc_files = [target_path]
    else:
        doc_files = sorted(
            [f for f in target_path.rglob("*") if f.is_file() and f.suffix.lower() in (".txt", ".pdf", ".docx", ".md")],
            key=lambda p: str(p),
        )
    print(f"Found {len(doc_files)} candidate documents in {target_path}", flush=True)

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    total_chunks = 0
    accepted_docs = 0
    rejected_docs = 0

    for idx, doc_file in enumerate(doc_files, 1):
        print(f"  [{idx}/{len(doc_files)}] Processing: {doc_file.name}...", end=" ", flush=True)
        try:
            doc = parse_and_validate_document(str(doc_file))
            if doc is None:
                print("skipped (empty/unreadable)")
                continue
            async with session_factory() as session:
                num_chunks = await store_ingested_document(doc, session)
            tier_label = "Placeholder" if doc.is_placeholder else f"Tier {doc.source_tier}"
            print(f"✓ [{tier_label}] '{doc.title}' ({num_chunks} chunks)", flush=True)
            total_chunks += num_chunks
            accepted_docs += 1
        except ValueError as e:
            print(f"✗ REJECTED: {e}", flush=True)
            rejected_docs += 1
        except Exception as e:
            print(f"✗ Error: {e}", flush=True)
            rejected_docs += 1

    await engine.dispose()

    print("-" * 80, flush=True)
    print(f"Ingestion complete: {accepted_docs} accepted, {rejected_docs} rejected. Total chunks: {total_chunks}", flush=True)
    print("=" * 80, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
