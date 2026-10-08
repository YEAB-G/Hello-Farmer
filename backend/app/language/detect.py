"""Language detection and caller language preference resolution for Amharic and Afaan Oromo."""
import logging
import re

logger = logging.getLogger("hello_farmer.language")

# Ge'ez Unicode Block: U+1200 - U+137F
GEEZ_REGEX = re.compile(r"[\u1200-\u137F]")

# Common Afaan Oromo grammatical markers and agricultural vocabulary in Latin script
OROMO_KEYWORDS = {
    # Greetings & Conversation
    "akkam", "nagaa", "fayyaa", "eeyyee", "lakki", "maaloo", "ani", "ati",
    "keessan", "keenya", "isaa", "ishee", "gaaffii", "deebii", "galatoomaa",
    # Language indicators
    "oromoo", "afaan", "oromiffa", "oromiyaa", "dubbachuu",
    # Agricultural & Environment
    "qonnaa", "qotee", "bulaa", "boqqoolloo", "xaafii", "qamadii", "garbuu",
    "buna", "baaqelaa", "midhaan", "sanyii", "biyyo", "biyyoo",
    "rooba", "bokkaa", "bubbee", "aduu", "lolaa", "bishaan",
    # Symptoms & Protection
    "dhibee", "keelloo", "baala", "baalli", "magaala", "goggogaa",
    "qoricha", "biifuu", "fufuu", "ilbiisa", "hawaannisa", "tortore",
    # Connectives & Prepositions
    "irra", "keessa", "irratti", "hanga", "gara", "akkamitti", "maaliif",
    "hin", "miti", "jira", "jiru", "qaba", "ta'e", "ta'a"
}

# Amharic spoken language markers
AMHARIC_SPOKEN_MARKERS = {
    "አማርኛ", "ሰላም", "ጤና ይስጥልኝ", "አዎ", "አይደለም", "እባክዎን", "እንደምን", "ጤፍ", "ስንዴ", "በቆሎ"
}


def detect_text_language(text: str, stored_preference: str | None = None) -> tuple[str, float]:
    """Detect language of text utterance between Amharic ('am') and Afaan Oromo ('om').

    Returns:
        (language_code, confidence): e.g. ('am', 0.98) or ('om', 0.95)
    """
    if not text or not text.strip():
        if stored_preference in ("am", "om"):
            return stored_preference, 0.70
        return "am", 0.50

    cleaned = text.strip()

    # 1. Check for Ge'ez script characters
    geez_chars = len(GEEZ_REGEX.findall(cleaned))
    total_alpha = len([c for c in cleaned if c.isalpha()])

    if total_alpha > 0 and (geez_chars / total_alpha) > 0.25:
        # Check if caller specifically asked for Afaan Oromo in Ge'ez (e.g. "ኦሮምኛ")
        if "ኦሮምኛ" in cleaned or "ኦሮሚፋ" in cleaned:
            return "om", 0.90
        return "am", 0.98

    # 2. Check for Afaan Oromo indicators in Latin text
    words = [w.lower().strip(".,?!'\"") for w in re.findall(r"[\w']+", cleaned)]
    if not words:
        if stored_preference in ("am", "om"):
            return stored_preference, 0.70
        return "am", 0.50

    oromo_matches = sum(1 for w in words if w in OROMO_KEYWORDS)
    match_ratio = oromo_matches / max(1, len(words))

    # Explicit language mention check
    if any(k in words for k in ["oromoo", "oromiffa", "afaan"]):
        return "om", 0.99

    if oromo_matches >= 2 or match_ratio >= 0.20:
        return "om", 0.95
    elif oromo_matches == 1:
        return "om", 0.80

    # 3. If caller has an existing verified preference, retain it
    if stored_preference in ("am", "om"):
        return stored_preference, 0.75

    # Default fallback
    return "am", 0.60


def format_language_switch_confirmation(target_language: str) -> str:
    """Return confirmation prompt when language is switched."""
    if target_language == "om":
        return "Afaan Oromootti jijjiirameera. Maaloo gaaffii keessan gaafadha."
    return "ወደ አማርኛ ተቀይሯል። እባክዎ ጥያቄዎን ይጠይቁ።"
