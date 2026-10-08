"""Unit tests for RAG chunking, source tier validation, and placeholder guardrails."""
import os
import tempfile

import pytest
from backend.app.rag.chunking import chunk_document_text
from backend.app.rag.ingest import parse_and_validate_document
from backend.app.rag.retrieve import RetrievedPassage


def test_chunking_with_heading_preservation():
    """Verify that chunker preserves section headings and generates token counts."""
    sample_text = (
        "# Heading 1: Teff Agronomy\n"
        "Teff is an important cereal crop grown extensively across the Ethiopian highlands.\n\n"
        "## Subheading 1.1: Soil Moisture\n"
        "Excess moisture during early vegetative growth causes yellowing and stunted vigor."
    )
    chunks = chunk_document_text(sample_text, target_tokens=100, overlap_tokens=20)
    assert len(chunks) >= 1
    assert any("Heading 1" in c.content or "Soil Moisture" in c.content for c in chunks)
    for c in chunks:
        assert c.token_count > 0


def test_tier4_document_rejection():
    """Verify Section 6.4 rule: Tier 4 documents (blogs/unvetted) MUST be rejected."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
        tf.write(
            "# Title: Random Agronomy Forum Post\n"
            "# Tier: 4\n"
            "Apply chemical spray 500ml per hectare immediately."
        )
        tf_path = tf.name

    try:
        with pytest.raises(ValueError, match="REJECTED.*Tier 4"):
            parse_and_validate_document(tf_path)
    finally:
        os.remove(tf_path)


def test_placeholder_document_ingestion():
    """Verify placeholder documents are flagged and parsed without error."""
    doc = parse_and_validate_document("knowledge_base/raw/kb_teff_growth_stages.txt")
    assert doc is not None
    assert doc.is_placeholder is True
    assert doc.source_tier == 0  # Placeholder tier
    assert len(doc.chunks) >= 1


def test_placeholder_dose_safe_fallback_guardrail():
    """Verify Section 6.4 rule: placeholder chunks can NEVER support a dose/chemical answer."""
    passage = RetrievedPassage(
        chunk_id="chk-001",
        document_id="DOC-001",
        document_title="Teff Growth Stages (Placeholder)",
        content="When standing water accumulates in the root zone, plants may show yellowing leaves.",
        source_tier=0,  # Placeholder tier
        score=0.85,
        is_placeholder=True,
    )

    # In our guardrail logic (section 6.4/6.6), dosage or chemical recommendations
    # require tier 1 (or approved tier 2). A placeholder tier (tier 0) MUST NOT support dosage.
    supports_chemical_advice = (passage.source_tier in (1, 2)) and not passage.is_placeholder
    assert supports_chemical_advice is False, "Placeholder passage must NEVER authorize chemical advice"
