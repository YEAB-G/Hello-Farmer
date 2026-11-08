"""Language detection strictly limited to four Ethiopian agricultural languages:
- English ('en')
- Amharic ('am')
- Tigrigna ('ti')
- Somali ('so')
"""
import logging
import re

logger = logging.getLogger("hello_farmer.language")

# Ge'ez Unicode Block: U+1200 - U+137F
GEEZ_REGEX = re.compile(r"[\u1200-\u137F]")

# Distinctive Tigrigna characters (not found in modern Amharic orthography)
TIGRINYA_CHARS = set("ቐቑቒቓቔቕቖኸኹኺኻኼኽኾዀዄዅዂጘጙጚጛጜጝጞ")

TIGRINYA_WORDS = {
    "እንታይ", "ከመይ", "ኣለኹ", "ኣለኻ", "ኣሎ", "ናይ", "ኣብ", "ማይ", "ሰብሊ", "ሕርሻ",
    "ጸገም", " እዩ", "እያ", "እዮም", "ድዩ", "ድያ", "ጣፍ", "ስርናይ", "ትግርኛ", "ደሓን", "ሰላም"
}

AMHARIC_WORDS = {
    "ምንድን", "እንዴት", "ነው", "ናት", "ናቸው", "ውስጥ", "ላይ", "ጋር", "ጤፍ", "ስንዴ",
    "በቆሎ", "አማርኛ", "ሰላም", "ጤና", "ይስጥልኝ", "ምን", "ላድርግ", "ማዳበሪያ", "ይቻላል"
}

SOMALI_WORDS = {
    "maxaa", "sidee", "waa", "ku", "ka", "ee", "oo", "iyo", "beeraha", "abuurka",
    "dhibaatada", "roobka", "biyaha", "cudurka", "dhirta", "ciidda", "soomaali",
    "maxaan", "waxaan", "fadlan", "mahadsanid", "galley", "qamadi", "beeraleyda"
}

OROMO_WORDS = {
    "akkam", "akkamitt", "maali", "rakkoo", "qonnaa", "ooyiruu", "midhaan", "xaafii",
    "qamadii", "boqqoolloo", "biyya", "galatoomaa", "nagaatti", "biyyee", "rooba",
    "bishaan", "dhibee", "baala", "keelloo", "isin", "gargaaruu", "danda'a", "jira"
}

ENGLISH_WORDS = {
    "what", "how", "why", "when", "is", "are", "the", "and", "to", "in", "on", "for",
    "crop", "farm", "farming", "fertilizer", "leaf", "leaves", "yellow", "disease",
    "soil", "weather", "teff", "wheat", "maize", "corn", "help", "hello", "please"
}

ALLOWED_LANGUAGES = ("en", "am", "om", "ti", "so")


def detect_text_language(text: str, stored_preference: str | None = None) -> tuple[str, float]:
    """Detect language of text utterance strictly among ('en', 'am', 'om', 'ti', 'so').

    Returns:
        (language_code, confidence): e.g. ('am', 0.98), ('ti', 0.95), ('om', 0.95), ('en', 0.95), ('so', 0.95)
    """
    if not text or not text.strip():
        if stored_preference in ALLOWED_LANGUAGES:
            return stored_preference, 0.70
        return "am", 0.50

    cleaned = text.strip()

    # 1. Ge'ez Script Analysis -> Amharic ('am') vs Tigrigna ('ti')
    geez_chars = len(GEEZ_REGEX.findall(cleaned))
    total_alpha = len([c for c in cleaned if c.isalpha()])

    if total_alpha > 0 and (geez_chars / total_alpha) > 0.25:
        # Check for Tigrigna characters or vocabulary
        has_ti_char = any(c in TIGRINYA_CHARS for c in cleaned)
        words = set(re.findall(r"[\u1200-\u137F]+", cleaned))
        ti_matches = sum(1 for w in words if w in TIGRINYA_WORDS)
        am_matches = sum(1 for w in words if w in AMHARIC_WORDS)

        if has_ti_char or ti_matches > am_matches or "ትግርኛ" in cleaned:
            return "ti", 0.95
        return "am", 0.98

    # 2. Latin Script Analysis -> English ('en') vs Afaan Oromo ('om') vs Somali ('so')
    latin_words = [w.lower().strip(".,?!'\"") for w in re.findall(r"[\w']+", cleaned)]
    if latin_words:
        om_matches = sum(1 for w in latin_words if w in OROMO_WORDS)
        so_matches = sum(1 for w in latin_words if w in SOMALI_WORDS)
        en_matches = sum(1 for w in latin_words if w in ENGLISH_WORDS)

        if om_matches > so_matches and om_matches > en_matches:
            return "om", 0.95
        if so_matches > en_matches:
            return "so", 0.95
        if en_matches > 0:
            return "en", 0.95

    # 3. Fallback to stored preference if valid
    if stored_preference in ALLOWED_LANGUAGES:
        return stored_preference, 0.75

    # Default fallback
    return "am", 0.60


def format_language_switch_confirmation(target_language: str) -> str:
    """Return confirmation prompt when language is switched."""
    if target_language == "om":
        return "Gara Afaan Oromootti jijjiirameera. Maaloo gaaffii keessan gaafadhaa."
    elif target_language == "ti":
        return "ናብ ትግርኛ ተቐይሩ ኣሎ። እባክኹም ሕቶኹም ሕተቱ።"
    elif target_language == "so":
        return "Waxa loo beddelay Af-Soomaali. Fadlan weydii su'aashaada."
    elif target_language == "en":
        return "Switched to English. Please ask your agricultural question."
    return "ወደ አማርኛ ተቀይሯል። እባክዎ ጥያቄዎን ይጠይቁ።"
