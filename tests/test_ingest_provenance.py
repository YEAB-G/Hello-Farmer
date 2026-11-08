"""Automated tests for Knowledge Ingestion Provenance & Trust Tiering (Phase 5)."""
import os
import tempfile
import pytest

from app.rag.ingest import extract_metadata_from_text, parse_and_validate_document


def test_moa_official_directory_provenance():
    """Verify that documents from official MoA directories receive Tier 1 status."""
    meta = extract_metadata_from_text(
        "Teff agronomy package for national highland zones.",
        "knowledge_base/raw/MoA Guidelines/teff_production_manual.txt",
    )
    assert meta["publisher"] == "Ministry of Agriculture, Ethiopia (MoA)"
    assert meta["source_tier"] == 1


def test_eiar_and_ess_directory_provenance():
    """Verify EIAR and ESS sources are mapped to Tier 1."""
    meta_eiar = extract_metadata_from_text(
        "Wheat rust resistance breeding trials.",
        "knowledge_base/raw/EIAR/wheat_rust_trials_2023.txt",
    )
    assert meta_eiar["source_tier"] == 1
    assert "EIAR" in meta_eiar["publisher"] or "Ethiopian Institute of Agricultural Research" in meta_eiar["publisher"]

    meta_ess = extract_metadata_from_text(
        "Annual agricultural sample survey report.",
        "knowledge_base/raw/ESS Data/ag_sample_survey.txt",
    )
    assert meta_ess["source_tier"] == 1
    assert "Ethiopian Statistical Service" in meta_ess["publisher"]


def test_fao_and_cgiar_tier2_provenance():
    """Verify international multilateral agricultural centers receive Tier 2 status."""
    meta_fao = extract_metadata_from_text(
        "Desert locust early warning and surveillance protocol.",
        "knowledge_base/raw/fao/desert_locust_handbook.txt",
    )
    assert meta_fao["source_tier"] == 2
    assert "FAO" in meta_fao["publisher"]

    # CGIAR via header
    cgiar_text = (
        "# Title: Forage Legumes for Highland Dairy\n"
        "# Publisher: International Livestock Research Institute (ILRI / CGIAR)\n"
        "Forage options for mid-altitude milk production."
    )
    meta_cgiar = extract_metadata_from_text(cgiar_text, "uploads/ilri_forage.txt")
    assert meta_cgiar["source_tier"] == 2
    assert "ILRI" in meta_cgiar["publisher"] or "CGIAR" in meta_cgiar["publisher"]


def test_academic_tier3_provenance():
    """Verify university agricultural faculty publications receive Tier 3 status."""
    uni_text = (
        "# Title: Soil Acidification in Western Oromia\n"
        "# Publisher: Haramaya University College of Agriculture\n"
        "Lime application rates across acidic soils."
    )
    meta_uni = extract_metadata_from_text(uni_text, "uploads/haramaya_soil_study.txt")
    assert meta_uni["source_tier"] == 3


def test_unverified_document_without_publisher_is_rejected():
    """Verify GAP-08 & Rule 10: Unknown documents are NOT defaulted to MoA and are rejected."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
        tf.write(
            "Some random unverified agricultural blog advice about adding salt to irrigation water.\n"
            "This has no official header or recognized publisher."
        )
        tf_path = tf.name

    try:
        # 1. Metadata check: Must NOT default to MoA
        meta = extract_metadata_from_text("Random blog text", tf_path)
        assert meta["source_tier"] == 4, "Unvetted upload must be classified as Tier 4!"
        assert meta["publisher"] != "Ministry of Agriculture, Ethiopia (MoA)", "Unvetted doc must never be falsely attributed to MoA!"

        # 2. Validation check: parse_and_validate_document must raise ValueError
        with pytest.raises(ValueError, match="REJECTED.*Tier 4"):
            parse_and_validate_document(tf_path)
    finally:
        os.remove(tf_path)


def test_sha256_cryptographic_checksum_computation():
    """Verify that validated documents compute and store SHA-256 integrity checksum."""
    doc = parse_and_validate_document("knowledge_base/raw/kb_teff_growth_stages.txt")
    assert doc is not None
    assert hasattr(doc, "sha256_hash")
    assert len(doc.sha256_hash) == 64, "Expected valid 64-char hex SHA-256 hash"
    assert int(doc.sha256_hash, 16) > 0

