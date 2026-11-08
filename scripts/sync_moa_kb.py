"""Synchronize and ingest agricultural manuals from external directory (e.g. C:\\Users\\user\\Downloads\\MOA) into Hello Farmer RAG knowledge base."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def sync_and_ingest(source_dir: str):
    source_path = Path(source_dir)
    if not source_path.exists():
        print(f"Error: Source directory '{source_path}' does not exist.")
        sys.exit(1)

    project_root = Path(__file__).resolve().parent.parent
    dest_dir = project_root / "knowledge_base" / "raw" / "MoA Guidelines"
    dest_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("🌾 HELLO FARMER: MOA KNOWLEDGE BASE SYNC & INGESTION")
    print(f"   Source:      {source_path}")
    print(f"   Destination: {dest_dir}")
    print("=" * 80)

    # 1. Copy files
    supported_extensions = {".pdf", ".docx", ".doc", ".txt", ".md"}
    source_files = [f for f in source_path.iterdir() if f.is_file() and f.suffix.lower() in supported_extensions]

    copied_count = 0
    skipped_count = 0

    for file in source_files:
        dest_file = dest_dir / file.name
        if not dest_file.exists() or file.stat().st_mtime > dest_file.stat().st_mtime:
            shutil.copy2(file, dest_file)
            copied_count += 1
            print(f"  [+] Copied: {file.name}")
        else:
            skipped_count += 1

    print(f"\n📁 File sync complete: {copied_count} copied/updated, {skipped_count} up-to-date.")
    print("-" * 80)

    # 2. Run ingestion inside the backend docker container
    print("🚀 Triggering vector ingestion inside 'hello_farmer_backend' container...")
    cmd = [
        "docker", "exec", "hello_farmer_backend",
        "python", "scripts/ingest_kb.py", "knowledge_base/raw/MoA Guidelines"
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing container ingestion: {e}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        # If docker CLI not in current python path, run locally
        local_cmd = [sys.executable, str(project_root / "scripts" / "ingest_kb.py"), str(dest_dir)]
        subprocess.run(local_cmd, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync and ingest MoA documents into Hello Farmer RAG")
    parser.add_argument(
        "source",
        nargs="?",
        default=r"C:\Users\user\Downloads\MOA",
        help="Path to source MoA documents directory (default: C:\\Users\\user\\Downloads\\MOA)"
    )
    args = parser.parse_args()
    sync_and_ingest(args.source)
