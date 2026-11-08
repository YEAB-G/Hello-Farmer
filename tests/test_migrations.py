"""Automated tests for Alembic Database Migrations (Phase 6)."""
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.database.models import Base


def test_alembic_configuration_and_script_directory():
    """Verify GAP-12: Alembic configuration and versions directory are valid."""
    root_ini = Path("alembic.ini")
    backend_ini = Path("backend/alembic.ini")
    assert root_ini.exists() or backend_ini.exists(), "alembic.ini not found!"

    chosen_ini = str(root_ini if root_ini.exists() else backend_ini)
    alembic_cfg = Config(chosen_ini)
    script = ScriptDirectory.from_config(alembic_cfg)

    # Verify head revision is 0001_initial_schema
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == "0001_initial_schema"

    # Verify revision metadata
    rev = script.get_revision("0001_initial_schema")
    assert rev is not None
    assert "pgvector" in rev.doc or "initial" in rev.doc.lower()


def test_target_metadata_includes_core_models():
    """Verify that Alembic target_metadata contains all core application tables."""
    tables = Base.metadata.tables.keys()
    required_tables = [
        "farmers",
        "farmer_context",
        "calls",
        "conversation_messages",
        "agricultural_documents",
        "knowledge_chunks",
        "warnings",
        "sms_messages",
    ]
    for table_name in required_tables:
        assert table_name in tables, f"Expected table '{table_name}' in Base.metadata!"

