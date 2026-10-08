"""Agricultural document chunking logic.

Chunks text into 300-500 token passages with overlap while preserving
section heading hierarchies and document metadata.
"""
import re
from typing import Any

from pydantic import BaseModel


class TextChunk(BaseModel):
    content: str
    chunk_index: int
    section_heading: str = "General"
    token_count: int
    crop: str = "general"
    topic: str = "general"
    page_number: int = 1


def approximate_token_count(text: str) -> int:
    """Approximate token count for mixed Ge'ez, Latin, and English text."""
    # Words separated by spaces + Ge'ez word divider
    words = re.findall(r"\S+", text)
    return len(words)


def chunk_document_text(
    full_text: str,
    target_tokens: int = 400,
    overlap_tokens: int = 50,
    default_crop: str = "general",
    default_topic: str = "general",
) -> list[TextChunk]:
    """Chunk document text into overlapping segments with preserved headings."""
    if not full_text or not full_text.strip():
        return []

    lines = full_text.split("\n")
    sections: list[dict[str, Any]] = []
    current_heading = "General Overview"
    current_lines: list[str] = []
    current_page = 1

    # Detect section headings and pages
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Page detection
        page_match = re.match(r"(?:===|---|Page)\s*PAGE?\s*(\d+)", stripped, re.IGNORECASE)
        if page_match:
            current_page = int(page_match.group(1))
            continue

        # Heading detection (#, ##, or Title:)
        heading_match = re.match(r"^(?:#{1,3}|Title:|Section:)\s*(.+)$", stripped, re.IGNORECASE)
        if heading_match:
            if current_lines:
                sections.append({
                    "heading": current_heading,
                    "text": "\n".join(current_lines),
                    "page": current_page,
                })
                current_lines = []
            current_heading = heading_match.group(1).strip()
        else:
            current_lines.append(stripped)

    if current_lines:
        sections.append({
            "heading": current_heading,
            "text": "\n".join(current_lines),
            "page": current_page,
        })

    # Chunk sections into overlapping token segments
    chunks: list[TextChunk] = []
    chunk_counter = 0

    for sec in sections:
        sec_heading = sec["heading"]
        sec_text = sec["text"]
        words = sec_text.split()

        if len(words) <= target_tokens:
            content = f"[{sec_heading}]\n{sec_text}"
            chunks.append(
                TextChunk(
                    content=content,
                    chunk_index=chunk_counter,
                    section_heading=sec_heading,
                    token_count=len(words),
                    crop=default_crop,
                    topic=default_topic,
                    page_number=sec["page"],
                )
            )
            chunk_counter += 1
        else:
            # Sliding window with overlap
            start = 0
            while start < len(words):
                end = min(start + target_tokens, len(words))
                chunk_words = words[start:end]
                chunk_body = " ".join(chunk_words)
                content = f"[{sec_heading}]\n{chunk_body}"
                chunks.append(
                    TextChunk(
                        content=content,
                        chunk_index=chunk_counter,
                        section_heading=sec_heading,
                        token_count=len(chunk_words),
                        crop=default_crop,
                        topic=default_topic,
                        page_number=sec["page"],
                    )
                )
                chunk_counter += 1
                if end == len(words):
                    break
                start += target_tokens - overlap_tokens

    return chunks
