"""Amharic text processing, normalization, and bidirectional number conversion.

Features:
- Unicode normalization (NFC) and punctuation cleaning.
- Evaluation normalization: folding phonetically confusable Amharic letters
  (ሀ/ሐ/ኀ -> ሀ, ሠ/ሰ -> ሰ, አ/ዐ -> አ, ፀ/ጸ -> ጸ) across all 7 orders.
- Bidirectional numbers:
    number_to_amharic_words(n) -> Spoken words (e.g. 25 -> ሃያ አምስት)
    amharic_words_to_number(text) -> Integer (e.g. "ሃያ አምስት" -> 25)
- Extraction of quantities with units (kg, ሄክታር, ኩንታል, ሊትር).
"""
import re
import unicodedata

# Mapping of phonetic equivalents to canonical forms (all 7 Ge'ez orders)
# Order 1 to 7: ግዕዝ, ካዕብ, ሳልስ, ራብዕ, ኃምስ, ሳድስ, ሳብዕ
CONFUSABLE_MAP = {
    # ሐ series -> ሀ series
    'ሐ': 'ሀ', 'ሑ': 'ሁ', 'ሒ': 'ሂ', 'ሓ': 'ሃ', 'ሔ': 'ሄ', 'ሕ': 'ህ', 'ሖ': 'ሆ',
    # ኀ series -> ሀ series
    'ኀ': 'ሀ', 'ኁ': 'ሁ', 'ኂ': 'ሂ', 'ኃ': 'ሃ', 'ኄ': 'ሄ', 'ኅ': 'ህ', 'ኆ': 'ሆ',
    # ሠ series -> ሰ series
    'ሠ': 'ሰ', 'ሡ': 'ሱ', 'ሢ': 'ሲ', 'ሣ': 'ሳ', 'ሤ': 'ሴ', 'ሥ': 'ስ', 'ሦ': 'ሶ',
    # ዐ series -> አ series
    'ዐ': 'አ', 'ዑ': 'ኡ', 'ዒ': 'ኢ', 'ዓ': 'ኣ', 'ዔ': 'ኤ', 'ዕ': 'እ', 'ዖ': 'ኦ',
    # ፀ series -> ጸ series
    'ፀ': 'ጸ', 'ፁ': 'ጹ', 'ፂ': 'ጺ', 'ፃ': 'ጻ', 'ፄ': 'ጼ', 'ፅ': 'ጽ', 'ፆ': 'ጾ',
}

# Ethiopic digits to integer
ETHIOPIC_NUMERALS = {
    '፩': 1, '፪': 2, '፫': 3, '፬': 4, '፭': 5,
    '፮': 6, '፯': 7, '፰': 8, '፱': 9, '፲': 10,
    '፳': 20, '፴': 30, '፵': 40, '፶': 50,
    '፷': 60, '፸': 70, '፹': 80, '፺': 90,
    '፻': 100, '፼': 10000
}

# Number words mappings
ONES_AM = {
    0: "ዜሮ",
    1: "አንድ",
    2: "ሁለት",
    3: "ሶስት",
    4: "አራት",
    5: "አምስት",
    6: "ስድስት",
    7: "ሰባት",
    8: "ስምንት",
    9: "ዘጠኝ",
}

TEENS_PREFIX = "አስራ "

TENS_AM = {
    10: "አስር",
    20: "ሃያ",
    30: "ሰላሳ",
    40: "አርባ",
    50: "ሃምሳ",
    60: "ስድሳ",
    70: "ሰባ",
    80: "ሰማንያ",
    90: "ዘጠና",
}

# Word to number inverse lookup
WORD_TO_NUM = {
    "ዜሮ": 0, "አንድ": 1, "አንዲት": 1, "ሁለት": 2, "ሶስት": 3,
    "አራት": 4, "አምስት": 5, "ስድስት": 6, "ሰባት": 7, "ስምንት": 8, "ዘጠኝ": 9,
    "አስር": 10, "አስራ": 10, "ሃያ": 20, "ሰላሳ": 30, "አርባ": 40, "ሃምሳ": 50,
    "ስድሳ": 60, "ሰባ": 70, "ሰማንያ": 80, "ዘጠና": 90,
    "መቶ": 100, "ሺህ": 1000, "ሺ": 1000, "ሚሊዮን": 1000000
}

# Common agricultural units in Amharic
UNITS_AMHARIC = {
    "ኪሎ": "kg",
    "ኪሎግራም": "kg",
    "ኪ.ግ": "kg",
    "ሄክታር": "hectare",
    "ኩንታል": "quintal",
    "ሊትር": "liter",
    "ሜትር": "meter",
    "ብር": "birr",
    "ቀን": "day",
    "ቀናት": "days",
    "ሳምንት": "week",
    "ወር": "month",
}


def normalize_amharic(text: str) -> str:
    """Standard unicode normalization and punctuation normalization for Amharic."""
    if not text:
        return ""
    # Unicode NFC normalization
    text = unicodedata.normalize("NFC", text)
    # Replace Ethiopic punctuation with standard spacing / periods
    text = text.replace("።", ". ").replace("፣", ", ").replace("፤", "; ")
    text = text.replace("፥", ": ").replace("፦", ": ").replace("፧", "? ")
    text = text.replace("፨", " ")
    # Normalize multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_amharic_for_eval(text: str) -> str:
    """Normalize Amharic text for evaluation (WER/CER calculation).

    Folds phonetically confusable characters so alternate spelling choices
    in Ge'ez script do not falsely penalize speech recognition.
    """
    text = normalize_amharic(text)
    # Strip punctuation
    text = re.sub(r"[^\w\s\u1200-\u137F]", "", text)
    # Fold confusable characters
    folded_chars = [CONFUSABLE_MAP.get(c, c) for c in text]
    result = "".join(folded_chars)
    return re.sub(r"\s+", " ", result).strip()


def number_to_amharic_words(n: int) -> str:
    """Convert an integer (0 to 999,999) into spoken Amharic words."""
    if n < 0:
        return "ከዜሮ በታች " + number_to_amharic_words(abs(n))
    if n <= 9:
        return ONES_AM[n]
    if n == 10:
        return TENS_AM[10]
    if 11 <= n <= 19:
        return TEENS_PREFIX + ONES_AM[n - 10]
    if 20 <= n <= 99:
        ten = (n // 10) * 10
        rem = n % 10
        if rem == 0:
            return TENS_AM[ten]
        return f"{TENS_AM[ten]} {ONES_AM[rem]}"
    if 100 <= n <= 999:
        hundreds = n // 100
        rem = n % 100
        prefix = f"{ONES_AM[hundreds]} መቶ" if hundreds > 1 else "አንድ መቶ"
        if rem == 0:
            return prefix
        return f"{prefix} {number_to_amharic_words(rem)}"
    if 1000 <= n <= 999999:
        thousands = n // 1000
        rem = n % 1000
        prefix = f"{number_to_amharic_words(thousands)} ሺህ"
        if rem == 0:
            return prefix
        return f"{prefix} {number_to_amharic_words(rem)}"
    return str(n)


def amharic_words_to_number(phrase: str) -> int | None:
    """Parse a phrase containing Amharic number words into an integer."""
    if not phrase:
        return None
    # If already digits
    cleaned = phrase.strip()
    if cleaned.isdigit():
        return int(cleaned)
    # Check Ethiopic digits
    if any(c in ETHIOPIC_NUMERALS for c in cleaned):
        total = 0
        for c in cleaned:
            if c in ETHIOPIC_NUMERALS:
                total += ETHIOPIC_NUMERALS[c]
        if total > 0:
            return total

    words = cleaned.split()
    total = 0
    current = 0

    # Common Amharic prefixes: ለ (for), በ (in/with), ከ (from), የ (of)
    PREPOSITIONS = ("ለ", "በ", "ከ", "የ")

    for raw_word in words:
        word = raw_word
        # Strip single preposition prefix if word not directly in dict
        if word not in WORD_TO_NUM and len(word) > 2 and word[0] in PREPOSITIONS:
            if word[1:] in WORD_TO_NUM:
                word = word[1:]

        if word in WORD_TO_NUM:
            val = WORD_TO_NUM[word]
            if val == 1000:
                current = (current if current != 0 else 1) * 1000
                total += current
                current = 0
            elif val == 100:
                current = (current if current != 0 else 1) * 100
            elif val == 10 and word == "አስራ":
                # Prefix like 'አስራ ሁለት'
                current += 10
            else:
                current += val
        else:
            return None if total == 0 and current == 0 else total + current

    return total + current



def extract_quantities_amharic(text: str) -> list[tuple[float, str]]:
    """Extract numeric quantities with their units from Amharic text.

    Returns list of (number, unit) tuples, e.g. [(2.0, 'hectare'), (50.0, 'kg')].
    Supports both digit form ("2 ሄክታር") and word form ("ሁለት ሄክታር").
    """
    results: list[tuple[float, str]] = []
    normalized = normalize_amharic(text)

    # 1. Match digits + unit: e.g. "2 ሄክታር", "50 ኪሎ"
    unit_pattern = r"(\d+(?:\.\d+)?)\s*(" + "|".join(re.escape(u) for u in UNITS_AMHARIC) + r")"
    for match in re.finditer(unit_pattern, normalized):
        val = float(match.group(1))
        unit = UNITS_AMHARIC[match.group(2)]
        results.append((val, unit))

    # 2. Match words + unit: e.g. "ሁለት ሄክታር", "ሃምሳ ኩንታል"
    words = normalized.split()
    for i, word in enumerate(words):
        if word in UNITS_AMHARIC:
            unit = UNITS_AMHARIC[word]
            # Look back up to 3 words for number phrase
            for lookback in range(1, min(4, i + 1)):
                phrase = " ".join(words[i - lookback:i])
                num = amharic_words_to_number(phrase)
                if num is not None:
                    # Prevent duplicate if already captured via digits
                    if not any(r[1] == unit and abs(r[0] - float(num)) < 0.01 for r in results):
                        results.append((float(num), unit))
                    break

    return results
