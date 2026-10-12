"""Agricultural text normalization for natural neural speech synthesis.

Prepares raw text from LLMs, RAG passages, or templates for Text-to-Speech:
1. Strips visual Markdown syntax (bold, asterisks, list markers, headers).
2. Expands agricultural units, dosages, chemicals, and acronyms phonetically.
3. Normalizes Ethiopic punctuation to induce natural speech cadence and pauses.
"""
import re


def normalize_text_for_tts(text: str, language: str = "am") -> str:
    """Normalize text into phonetically smooth form for TTS synthesis.

    Args:
        text: Raw input text (may contain Markdown, abbreviations, etc.)
        language: 'am' (Amharic) or 'om' (Afaan Oromo)

    Returns:
        Clean, phonetically expanded text ready for TTS synthesis.
    """
    if not text or not text.strip():
        return ""

    s = text.strip()

    # 1. Strip Markdown formatting
    # Headers (# Title, ## Title)
    s = re.sub(r"^#{1,6}\s*", "", s, flags=re.MULTILINE)
    # Bold / Italic (**text**, *text*, __text__, _text_)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    s = re.sub(r"__([^_]+)__", r"\1", s)
    s = re.sub(r"_([^_]+)_", r"\1", s)
    # Bullet points (* item, - item, • item)
    s = re.sub(r"^\s*[\*\-\•]\s+", "", s, flags=re.MULTILINE)
    # Numbered lists (1. Item -> Item or 1: Item)
    s = re.sub(r"^\s*\d+[\.\)]\s*", "", s, flags=re.MULTILINE)
    # Markdown links [text](url) -> text
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)

    if language == "am":
        # 2. Amharic Agricultural Acronyms & Hotlines
        s = re.sub(r"\b8028\b", "ስምንት ዜሮ ሁለት ስምንት", s)
        s = re.sub(r"\bDA\b", "የልማት ጣቢያ ባለሙያ", s)
        s = re.sub(r"\bNPS\b", "ኤን ፒ ኤስ", s)
        s = re.sub(r"\bDAP\b", "ዳፕ", s)
        s = re.sub(r"\bpH\b", "ፒ ኤች", s)

        # 3. Measurement Units Expansion
        # Kilograms
        s = re.sub(r"(\d+)\s*(?:kg|k\.g|ኪ\.ግ|ኪግ)\b", r"\1 ኪሎ ግራም", s, flags=re.IGNORECASE)
        # Grams
        s = re.sub(r"(\d+)\s*(?:g|ግ)\b", r"\1 ግራም", s, flags=re.IGNORECASE)
        # Milliliters
        s = re.sub(r"(\d+)\s*(?:ml|m\.l|ሚ\.ሊ|ሚሊ)\b", r"\1 ሚሊ ሊትር", s, flags=re.IGNORECASE)
        # Liters
        s = re.sub(r"(\d+)\s*(?:l|ሊ|ሊትር)\b", r"\1 ሊትር", s, flags=re.IGNORECASE)
        # Hectares
        s = re.sub(r"(\d+)\s*(?:ha|ሄ/ር)\b", r"\1 ሄክታር", s, flags=re.IGNORECASE)
        # Kilometers / Meters
        s = re.sub(r"(\d+)\s*(?:km|ኪ\.ሜ)\b", r"\1 ኪሎ ሜትር", s, flags=re.IGNORECASE)
        s = re.sub(r"(\d+)\s*(?:m|ሜ)\b", r"\1 ሜትር", s, flags=re.IGNORECASE)
        # Percentage
        s = re.sub(r"(\d+)\s*%", r"\1 በመቶ", s)

        # 4. Ethiopic Punctuation Cadence
        # Replace trailing periods with Ethiopic Arat Neteb (።)
        s = re.sub(r"\.(?=\s|$)", "።", s)
        # Replace commas with Netela Serez (፣)
        s = re.sub(r",\s*", "፣ ", s)
        # Replace semicolons with Derib Serez (፤)
        s = re.sub(r";\s*", "፤ ", s)

    elif language == "om":
        # Afaan Oromo Hotlines & Acronyms
        s = re.sub(r"\b8028\b", "saddeet duwwaa lama saddeet", s)
        s = re.sub(r"\bDA\b", "ogeessa misooma qonnaa", s)
        s = re.sub(r"\bNPS\b", "NPS", s)
        s = re.sub(r"\bDAP\b", "DAP", s)

        # Units
        s = re.sub(r"(\d+)\s*(?:kg|k\.g)\b", r"\1 kiiloo giraama", s, flags=re.IGNORECASE)
        s = re.sub(r"(\d+)\s*(?:ml)\b", r"\1 miilii liitira", s, flags=re.IGNORECASE)
        s = re.sub(r"(\d+)\s*(?:l)\b", r"\1 liitira", s, flags=re.IGNORECASE)
        s = re.sub(r"(\d+)\s*(?:ha)\b", r"\1 hektaara", s, flags=re.IGNORECASE)
        s = re.sub(r"(\d+)\s*%", r"\1 dhibbentaa", s)

    # Clean double punctuation or excessive spacing
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()
