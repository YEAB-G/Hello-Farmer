"""Download and extract MoA Ethiopia ISFM practice manuals into knowledge_base/raw."""
import os
import re
from pathlib import Path
import httpx
from pypdf import PdfReader

MANUALS = [
    {
        "url": "https://www.moa.gov.et/wp-content/uploads/2025/01/20230518_N-and-P-will-do.-An-effective-fertilizer-Strategy_eng_V4.pdf",
        "doc_id": "moa_np_fertilizer_strategy",
        "title": "MoA Ethiopia - N and P Will Do: An Effective Fertilizer Strategy",
        "year": 2023,
        "filename": "moa_np_fertilizer_strategy.md",
        "crop": "general"
    },
    {
        "url": "https://www.moa.gov.et/wp-content/uploads/2025/01/20240101_Cattle-Urine-Manual_English-version.pdf",
        "doc_id": "moa_cattle_urine_manual",
        "title": "MoA Ethiopia - Cattle Urine as Organic Liquid Fertilizer Manual",
        "year": 2024,
        "filename": "moa_cattle_urine_manual.md",
        "crop": "general"
    },
    {
        "url": "https://www.moa.gov.et/wp-content/uploads/2025/01/20201124_ISFM_Technical-Manual_English_updated.pdf",
        "doc_id": "moa_isfm_technical_manual",
        "title": "MoA Ethiopia - Integrated Soil Fertility Management Technical Manual",
        "year": 2020,
        "filename": "moa_isfm_technical_manual.md",
        "crop": "general"
    },
    {
        "url": "https://www.moa.gov.et/wp-content/uploads/2025/01/20160708_ISFMtechnical-implementation_Field-Guide_English.pdf",
        "doc_id": "moa_isfm_field_guide",
        "title": "MoA Ethiopia - ISFM Technical Implementation Field Guide",
        "year": 2016,
        "filename": "moa_isfm_field_guide.md",
        "crop": "general"
    }
]

def clean_extracted_text(text: str) -> str:
    # Remove excess whitespace and repeated page numbers/headers
    lines = [line.strip() for line in text.splitlines()]
    cleaned_lines = []
    for line in lines:
        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def download_and_extract():
    kb_raw = Path("knowledge_base/raw")
    kb_raw.mkdir(parents=True, exist_ok=True)
    temp_dir = Path("knowledge_base/temp_downloads")
    temp_dir.mkdir(parents=True, exist_ok=True)

    client = httpx.Client(verify=False, timeout=60.0, follow_redirects=True)

    for item in MANUALS:
        pdf_path = temp_dir / f"{item['doc_id']}.pdf"
        md_path = kb_raw / item["filename"]

        print(f"\nProcessing {item['title']}...")
        if not pdf_path.exists():
            print(f"  Downloading from {item['url']}...")
            try:
                resp = client.get(item["url"])
                resp.raise_for_status()
                with open(pdf_path, "wb") as f:
                    f.write(resp.content)
                print(f"  Saved PDF ({len(resp.content)} bytes).")
            except Exception as e:
                print(f"  Failed to download {item['url']}: {e}")
                continue
        else:
            print(f"  Using cached PDF: {pdf_path}")

        print("  Extracting text from PDF...")
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            print(f"  Total pages: {total_pages}")
            page_texts = []
            for idx, page in enumerate(reader.pages):
                txt = page.extract_text()
                if txt:
                    page_texts.append(f"\n### Section / Page {idx + 1}\n{txt}")

            full_body = clean_extracted_text("\n\n".join(page_texts))

            header = (
                f"# Document ID: {item['doc_id']}\n"
                f"# Title: {item['title']}\n"
                f"# Publisher: FDRE Ministry of Agriculture\n"
                f"# Year: {item['year']}\n"
                f"# Tier: 1\n"
                f"# Language: en/am\n"
                f"# Crop: {item['crop']}\n"
                f"# Region: Ethiopia\n\n"
                f"# {item['title']}\n"
                f"**Source**: FDRE Ministry of Agriculture (MoA Ethiopia ISFM Practice Manuals - https://www.moa.gov.et/isfm-practice-manuals/)\n"
                f"**Verification**: Official Government Technical Manual (Tier 1 Verified)\n\n"
            )

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(header + full_body)

            print(f"  Successfully saved markdown: {md_path} ({len(full_body)} chars)")
        except Exception as e:
            print(f"  Error extracting text from {pdf_path}: {e}")

if __name__ == "__main__":
    download_and_extract()
