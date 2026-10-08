"""Document ingestion pipeline with Source Tier validation.

Validates source tiers (Tiers 1-3 allowed, Tier 4 strictly rejected),
extracts metadata, chunks text, and stores records in PostgreSQL pgvector.
"""
from pathlib import Path
from typing import Any

from pydantic import BaseModel

try:
    from app.rag.chunking import TextChunk, chunk_document_text
except ImportError:
    from backend.app.rag.chunking import TextChunk, chunk_document_text


class IngestedDocument(BaseModel):
    document_id: str
    title: str
    publisher: str | None = None
    publication_year: int | None = None
    source_tier: int  # 1 (MoA/Gov), 2 (FAO/CGIAR), 3 (Academic), 4 (Rejected)
    is_placeholder: bool = False
    language: str = "am"
    crop: str = "general"
    region: str = "national"
    file_path: str
    chunks: list[TextChunk] = []


def extract_metadata_from_text(raw_text: str, file_path: str) -> dict[str, Any]:
    """Parse header comments or frontmatter from document text."""
    metadata = {
        "document_id": Path(file_path).stem,
        "title": Path(file_path).stem.replace("_", " ").title(),
        "publisher": "Unknown",
        "publication_year": 2026,
        "source_tier": 1,
        "is_placeholder": False,
        "language": "am",
        "crop": "general",
        "region": "Ethiopia",
    }

    # Detect placeholder notices
    if "PLACEHOLDER" in raw_text.upper():
        metadata["is_placeholder"] = True
        metadata["source_tier"] = 0  # Placeholder tier
        metadata["publisher"] = "Hello Farmer Evaluation Team (Placeholder)"

    # Look for key-value headers
    for line in raw_text.split("\n")[:20]:
        line_clean = line.strip().lstrip("#").strip()
        if ":" in line_clean:
            key, val = line_clean.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if "document id" in key or "doc id" in key:
                metadata["document_id"] = val
            elif "title" in key:
                metadata["title"] = val
            elif "publisher" in key:
                metadata["publisher"] = val
            elif "year" in key and val.isdigit():
                metadata["publication_year"] = int(val)
            elif "tier" in key:
                if "placeholder" in val.lower():
                    metadata["source_tier"] = 0
                    metadata["is_placeholder"] = True
                elif val.isdigit():
                    metadata["source_tier"] = int(val)
            elif "language" in key:
                metadata["language"] = val.split("/")[0].strip().lower()
            elif "crop" in key:
                metadata["crop"] = val.lower()

    # Detect crop from title or filename
    filename_lower = Path(file_path).name.lower()
    if "teff" in filename_lower or "xaafii" in filename_lower or "ጤፍ" in raw_text:
        metadata["crop"] = "teff"
    elif "maize" in filename_lower or "boqqoolloo" in filename_lower or "በቆሎ" in raw_text:
        metadata["crop"] = "maize"
    elif "wheat" in filename_lower or "qamadii" in filename_lower or "ስንዴ" in raw_text:
        metadata["crop"] = "wheat"

    return metadata


def parse_and_validate_document(file_path: str) -> IngestedDocument | None:
    """Parse document and enforce source tier validation rules."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read content
    if path.suffix.lower() == ".txt":
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    elif path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            content = "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    meta = extract_metadata_from_text(content, str(path))

    # ENFORCE SOURCE TIER VALIDATION (Section 6.4)
    # Tier 1: MoA/EIAR, Tier 2: FAO/CGIAR, Tier 3: University/Research, 0: Placeholder
    # Tier 4: Unverified / Blogs -> STRICTLY REJECTED
    tier = meta["source_tier"]
    if tier == 4 or tier > 3 and not meta["is_placeholder"]:
        raise ValueError(
            f"REJECTED: Document '{meta['title']}' is classified as Tier 4. "
            "Section 6.4 prohibits ingesting unvetted or Tier 4 documents."
        )

    # Chunk text
    chunks = chunk_document_text(
        content,
        target_tokens=400,
        overlap_tokens=50,
        default_crop=meta["crop"],
        default_topic=meta.get("topic", "general"),
    )

    return IngestedDocument(
        document_id=meta["document_id"],
        title=meta["title"],
        publisher=meta["publisher"],
        publication_year=meta["publication_year"],
        source_tier=tier,
        is_placeholder=meta["is_placeholder"],
        language=meta["language"],
        crop=meta["crop"],
        region=meta["region"],
        file_path=str(path),
        chunks=chunks,
    )
