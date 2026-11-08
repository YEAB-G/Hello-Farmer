"""Document ingestion pipeline with Source Tier validation.

Validates source tiers (Tiers 1-3 allowed, Tier 4 strictly rejected),
extracts metadata, chunks text, and stores records in PostgreSQL pgvector.
"""
import hashlib
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

try:
    from app.rag.chunking import TextChunk, chunk_document_text
except ImportError:
    from backend.app.rag.chunking import TextChunk, chunk_document_text

logger = logging.getLogger("hello_farmer.rag.ingest")


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
    sha256_hash: str = ""
    chunks: list[TextChunk] = []


def extract_metadata_from_text(raw_text: str, file_path: str) -> dict[str, Any]:
    """Parse header comments or frontmatter from document text and verify publisher provenance."""
    path_obj = Path(file_path)
    stem = path_obj.stem
    # Use deterministic 32-char hex MD5 so it reliably fits in String(36) DB column
    safe_doc_id = hashlib.md5(f"{path_obj.parent.name}/{stem}".encode("utf-8")).hexdigest()

    clean_title = stem.replace("_", " ").replace("-", " ").strip()
    if len(clean_title) > 240:
        clean_title = clean_title[:240]

    # Verify publisher & source tier based on strict provenance rules (Rule 10)
    path_str_lower = str(file_path).replace("\\", "/").lower()

    if "moa guidelines" in path_str_lower or "/moa/" in path_str_lower or stem.lower().startswith("moa"):
        publisher = "Ministry of Agriculture, Ethiopia (MoA)"
        tier = 1
    elif "eiar" in path_str_lower or "ethiopian institute of agricultural research" in path_str_lower:
        publisher = "Ethiopian Institute of Agricultural Research (EIAR)"
        tier = 1
    elif "ess data" in path_str_lower or "statistical service" in path_str_lower:
        publisher = "Ethiopian Statistical Service (ESS)"
        tier = 1
    elif "fao" in stem.lower() or "/fao/" in path_str_lower:
        publisher = "FAO / UN"
        tier = 2
    elif any(k in path_str_lower or k in stem.lower() for k in ["cgiar", "ilri", "cimmyt", "icarda"]):
        publisher = "CGIAR"
        tier = 2
    elif any(k in path_str_lower or k in stem.lower() for k in ["university", "haramaya", "hawassa", "bahir dar"]):
        publisher = "Academic / University Research"
        tier = 3
    else:
        # Default unknown/unverified documents to Tier 4 (never invent MoA provenance)
        publisher = "Unknown / Unverified"
        tier = 4

    metadata = {
        "document_id": safe_doc_id,
        "title": clean_title,
        "publisher": publisher,
        "publication_year": 2024,
        "source_tier": tier,
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
    for line in raw_text.split("\n")[:25]:
        line_clean = line.strip().lstrip("#").strip()
        if ":" in line_clean:
            key, val = line_clean.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if "document id" in key or "doc id" in key:
                if len(val) <= 36:
                    metadata["document_id"] = val
            elif "title" in key:
                metadata["title"] = val[:240]
            elif "publisher" in key:
                val_pub = val[:240].strip()
                metadata["publisher"] = val_pub
                pub_lower = val_pub.lower()
                # Classify publisher into verified tier
                if any(k in pub_lower for k in ["ministry of agriculture", "moa", "eiar", "ethiopian institute of agricultural research", "ess", "statistical service"]):
                    metadata["source_tier"] = 1
                elif any(k in pub_lower for k in ["fao", "cgiar", "ilri", "cimmyt", "icarda", "united nations", "world bank"]):
                    metadata["source_tier"] = 2
                elif any(k in pub_lower for k in ["university", "college", "journal", "academic", "institute"]):
                    metadata["source_tier"] = 3
                else:
                    metadata["source_tier"] = 4
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

    # Detect crop from title or filename or content
    filename_lower = path_obj.name.lower()
    text_sample = raw_text[:3000].lower()

    if any(k in filename_lower for k in ["tef", "teff", "xaafii"]) or "ጤፍ" in raw_text:
        metadata["crop"] = "teff"
    elif any(k in filename_lower for k in ["maize", "boqqoolloo", "corn"]) or "በቆሎ" in raw_text:
        metadata["crop"] = "maize"
    elif any(k in filename_lower for k in ["wheat", "qamadii", "durum"]) or "ስንዴ" in raw_text:
        metadata["crop"] = "wheat"
    elif any(k in filename_lower for k in ["barley", "garbuu"]) or "ገብስ" in raw_text:
        metadata["crop"] = "barley"
    elif any(k in filename_lower for k in ["sorghum", "misingaa"]) or "ማሽላ" in raw_text:
        metadata["crop"] = "sorghum"
    elif any(k in filename_lower for k in ["rice", "ruuzii"]) or "ሩዝ" in raw_text:
        metadata["crop"] = "rice"
    elif any(k in filename_lower for k in ["soybean", "soya"]) or "አኩሪ አተር" in raw_text:
        metadata["crop"] = "soybean"
    elif any(k in filename_lower for k in ["sesame", "selit"]) or "ሰሊጥ" in raw_text:
        metadata["crop"] = "sesame"
    elif any(k in filename_lower for k in ["peanut", "groundnut", "arachis"]) or "ለውዝ" in raw_text:
        metadata["crop"] = "groundnut"
    elif any(k in filename_lower for k in ["pulse", "pea", "bean", "lentil", "chickpea"]) or any(k in raw_text for k in ["ጥራጥሬ", "አተር", "ምስር", "ሽምብራ"]):
        metadata["crop"] = "pulses"
    elif any(k in filename_lower for k in ["millet", "dagusa"]) or "ዳጉሳ" in raw_text:
        metadata["crop"] = "millet"
    elif any(k in filename_lower for k in ["dairy", "livestock", "cattle"]) or any(k in raw_text for k in ["ከብት", "ወተት", "እንስሳት"]):
        metadata["crop"] = "livestock"

    return metadata


def parse_and_validate_document(file_path: str) -> IngestedDocument | None:
    """Parse document (.pdf, .docx, .txt, .md) and enforce source tier validation rules."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    content = ""

    # Read content according to file format
    if ext in (".txt", ".md"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            extracted_pages = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    extracted_pages.append(txt)
            content = "\n\n".join(extracted_pages)
        except Exception as e:
            logger.warning(f"pypdf extraction failed for {path.name}: {e}")
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            tables_text = []
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_cells:
                        tables_text.append(" | ".join(row_cells))
            content = "\n\n".join(paragraphs + tables_text)
        except Exception as e:
            logger.warning(f"docx extraction failed for {path.name}: {e}")
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    # If document has negligible text, skip
    if not content or len(content.strip()) < 30:
        logger.info(f"Skipping {path.name} (insufficient readable text: {len(content)} chars)")
        return None

    meta = extract_metadata_from_text(content, str(path))

    # ENFORCE SOURCE TIER VALIDATION (Section 6.4)
    # Tier 1: MoA/EIAR, Tier 2: FAO/CGIAR, Tier 3: University/Research, 0: Placeholder
    # Tier 4: Unverified / Blogs -> STRICTLY REJECTED
    tier = meta["source_tier"]
    if tier == 4 or (tier > 3 and not meta["is_placeholder"]):
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

    if not chunks:
        return None

    sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

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
        sha256_hash=sha256,
        chunks=chunks,
    )

