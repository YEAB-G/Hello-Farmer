"""Afaan Oromo text processing, normalization, and bidirectional number conversion.

Features:
- Latin Qubee normalization, glottal stop (hudhaa) apostrophe standardization.
- Normalization for evaluation (WER/CER).
- Bidirectional numbers:
    number_to_oromo_words(n) -> e.g. 25 -> digdamii shan
    oromo_words_to_number(phrase) -> Integer
- Extraction of quantities with units (hektaara, kiiloo, kuuntaala, liitira).
"""
import re
import unicodedata

ONES_OROMO = {
    0: "zeeroo",
    1: "tokko",
    2: "lama",
    3: "sadii",
    4: "afur",
    5: "shan",
    6: "ja'a",
    7: "torba",
    8: "saddeet",
    9: "sagal",
}

TENS_OROMO = {
    10: "kudhan",
    20: "digdama",
    30: "soddoma",
    40: "afurtama",
    50: "shantama",
    60: "jaatama",
    70: "torbaatama",
    80: "saddeettama",
    90: "sagaltama",
}

WORD_TO_NUM_OROMO = {
    "zeeroo": 0, "tokko": 1, "lama": 2, "sadii": 3, "afur": 4,
    "shan": 5, "ja'a": 6, "jaa": 6, "torba": 7, "saddeet": 8, "sagal": 9,
    "kudhan": 10, "kudha": 10, "digdama": 20, "digdamii": 20,
    "soddoma": 30, "soddomii": 30, "afurtama": 40, "afurtamii": 40,
    "shantama": 50, "shantamii": 50, "jaatama": 60, "jaatamii": 60,
    "torbaatama": 70, "torbaatamii": 70, "saddeettama": 80, "saddeettamii": 80,
    "sagaltama": 90, "sagaltamii": 90,
    "dhibba": 100, "kuma": 1000, "miliyoona": 1000000
}

UNITS_OROMO = {
    "kiiloo": "kg",
    "kg": "kg",
    "hektaara": "hectare",
    "kuuntaala": "quintal",
    "liitira": "liter",
    "meetira": "meter",
    "birrii": "birr",
    "guyyaa": "day",
    "torbee": "week",
    "ji'a": "month",
}


def normalize_oromo(text: str) -> str:
    """Standardize Afaan Oromo text: normalize unicode and glottal stop apostrophes."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    # Standardize all curly apostrophes and backticks to simple ASCII single quote
    text = re.sub(r"[’‘ʻ`´]", "'", text)
    # Remove excessive punctuation spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_oromo_for_eval(text: str) -> str:
    """Normalize Afaan Oromo text for evaluation (WER/CER calculation)."""
    text = normalize_oromo(text).lower()
    # Remove punctuation except internal apostrophes
    text = re.sub(r"[^\w\s']", "", text)
    return re.sub(r"\s+", " ", text).strip()


def number_to_oromo_words(n: int) -> str:
    """Convert an integer (0 to 999,999) into spoken Afaan Oromo words."""
    if n < 0:
        return "zeeroo gadi " + number_to_oromo_words(abs(n))
    if n <= 9:
        return ONES_OROMO[n]
    if n == 10:
        return TENS_OROMO[10]
    if 11 <= n <= 19:
        return f"kudha {ONES_OROMO[n - 10]}"
    if 20 <= n <= 99:
        ten = (n // 10) * 10
        rem = n % 10
        if rem == 0:
            return TENS_OROMO[ten]
        # In Oromo: digdama -> digdamii lama
        prefix = TENS_OROMO[ten].rstrip('a') + "ii"
        return f"{prefix} {ONES_OROMO[rem]}"
    if 100 <= n <= 999:
        hundreds = n // 100
        rem = n % 100
        prefix = f"dhibba {ONES_OROMO[hundreds]}" if hundreds > 1 else "dhibba tokko"
        if rem == 0:
            return prefix
        return f"{prefix} fi {number_to_oromo_words(rem)}"
    if 1000 <= n <= 999999:
        thousands = n // 1000
        rem = n % 1000
        prefix = f"kuma {number_to_oromo_words(thousands)}"
        if rem == 0:
            return prefix
        return f"{prefix} fi {number_to_oromo_words(rem)}"
    return str(n)


def oromo_words_to_number(phrase: str) -> int | None:
    """Parse Afaan Oromo number words into an integer."""
    if not phrase:
        return None
    cleaned = normalize_oromo_for_eval(phrase)
    if cleaned.isdigit():
        return int(cleaned)

    # In Oromo: 'dhibba tokko' is 100, 'kuma tokko' is 1000
    # 'fi' denotes addition: 'dhibba tokko fi lama' is 102
    tokens = cleaned.split()
    total = 0
    current = 0
    prev_was_base = False  # Track if immediately following dhibba or kuma

    for token in tokens:
        if token == "fi":
            prev_was_base = False
            continue

        if token in WORD_TO_NUM_OROMO:
            val = WORD_TO_NUM_OROMO[token]
            if val in (100, 1000):
                # If we had a preceding number (e.g. 'lama dhibba' or just 'dhibba')
                current = (current if current != 0 else 1) * val
                prev_was_base = True
            elif prev_was_base and val in (1, 2, 3, 4, 5, 6, 7, 8, 9):
                # E.g. 'dhibba tokko' -> 100 * 1 = 100, 'dhibba lama' -> 100 * 2 = 200
                if current in (100, 1000):
                    current = (current // 1) * val
                else:
                    current += val
                prev_was_base = False
            elif val == 10 and token == "kudha":
                current += 10
                prev_was_base = False
            else:
                current += val
                prev_was_base = False
        else:
            return None if total == 0 and current == 0 else total + current

    return total + current



def extract_quantities_oromo(text: str) -> list[tuple[float, str]]:
    """Extract numeric quantities with their units from Afaan Oromo text."""
    results: list[tuple[float, str]] = []
    normalized = normalize_oromo(text).lower()

    # 1. Match digits + unit: e.g. "2 hektaara", "50 kiiloo"
    unit_pattern = r"(\d+(?:\.\d+)?)\s*(" + "|".join(re.escape(u) for u in UNITS_OROMO) + r")"
    for match in re.finditer(unit_pattern, normalized):
        val = float(match.group(1))
        unit = UNITS_OROMO[match.group(2)]
        results.append((val, unit))

    # 2. Match words + unit: e.g. "lama hektaara", "shantama kiiloo"
    words = normalized.split()
    for i, word in enumerate(words):
        if word in UNITS_OROMO:
            unit = UNITS_OROMO[word]
            for lookback in range(1, min(4, i + 1)):
                phrase = " ".join(words[i - lookback:i])
                num = oromo_words_to_number(phrase)
                if num is not None:
                    if not any(r[1] == unit and abs(r[0] - float(num)) < 0.01 for r in results):
                        results.append((float(num), unit))
                    break

    return results
