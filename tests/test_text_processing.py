"""Unit tests for Amharic and Afaan Oromo text normalization and number conversions."""
from backend.app.text.amharic import (
    amharic_words_to_number,
    extract_quantities_amharic,
    normalize_amharic_for_eval,
    number_to_amharic_words,
)
from backend.app.text.oromo import (
    extract_quantities_oromo,
    normalize_oromo,
    normalize_oromo_for_eval,
    number_to_oromo_words,
    oromo_words_to_number,
)


def test_amharic_confusable_folding_for_eval():
    """Verify that Ge'ez confusable variants are normalized to canonical forms."""
    # ሐ series -> ሀ series
    assert "ሀ" in normalize_amharic_for_eval("ሐምሌ")
    # ሠ series -> ሰ series
    assert normalize_amharic_for_eval("ሠላም") == "ሰላም"
    # ዐ series -> አ series
    assert normalize_amharic_for_eval("ዐይነት") == "አይነት"
    # ፀ and ሐ series -> ጸ and ሀ
    assert normalize_amharic_for_eval("ፀሐይ") == "ጸሀይ"


def test_amharic_bidirectional_numbers():
    """Verify conversion of numbers to Amharic words and back to integers."""
    test_cases = [
        (0, "ዜሮ"),
        (1, "አንድ"),
        (2, "ሁለት"),
        (7, "ሰባት"),
        (10, "አስር"),
        (15, "አስራ አምስት"),
        (20, "ሃያ"),
        (25, "ሃያ አምስት"),
        (50, "ሃምሳ"),
        (100, "አንድ መቶ"),
        (350, "ሶስት መቶ ሃምሳ"),
        (1000, "አንድ ሺህ"),
        (2026, "ሁለት ሺህ ሃያ ስድስት"),
    ]

    for num, expected_words in test_cases:
        words = number_to_amharic_words(num)
        assert words == expected_words, f"Expected {expected_words}, got {words}"
        parsed_back = amharic_words_to_number(expected_words)
        assert parsed_back == num, f"Expected {num}, parsed back {parsed_back} from '{expected_words}'"


def test_amharic_quantity_extraction():
    """Verify extraction of quantities and units in both word and digit forms."""
    # Words
    text1 = "ለአንድ ሄክታር ሰብል ሃምሳ ኪሎ ማዳበሪያ ያስፈልጋል"
    quantities1 = extract_quantities_amharic(text1)
    assert (1.0, "hectare") in quantities1
    assert (50.0, "kg") in quantities1

    # Digits
    text2 = "በ 2 ሄክታር ማሳ ላይ 10 ኩንታል ጤፍ ተሰበሰበ"
    quantities2 = extract_quantities_amharic(text2)
    assert (2.0, "hectare") in quantities2
    assert (10.0, "quintal") in quantities2


def test_oromo_apostrophe_normalization():
    """Verify that glottal stop / hudhaa quotes are standardized."""
    assert normalize_oromo("ja’a") == "ja'a"
    assert normalize_oromo("ji‘a") == "ji'a"
    assert normalize_oromo_for_eval("Oromiyaa’tti!") == "oromiyaa'tti"


def test_oromo_bidirectional_numbers():
    """Verify Afaan Oromo number-to-words and words-to-number."""
    test_cases = [
        (0, "zeeroo"),
        (1, "tokko"),
        (2, "lama"),
        (5, "shan"),
        (10, "kudhan"),
        (15, "kudha shan"),
        (20, "digdama"),
        (25, "digdamii shan"),
        (50, "shantama"),
        (100, "dhibba tokko"),
        (1000, "kuma tokko"),
    ]

    for num, expected_words in test_cases:
        words = number_to_oromo_words(num)
        assert words == expected_words, f"Expected {expected_words}, got {words}"
        parsed_back = oromo_words_to_number(expected_words)
        assert parsed_back == num, f"Expected {num}, parsed back {parsed_back} from '{expected_words}'"


def test_oromo_quantity_extraction():
    """Verify extraction of quantities and units in Afaan Oromo."""
    text1 = "Lama hektaara irratti shantama kiiloo facaase"
    quantities1 = extract_quantities_oromo(text1)
    assert (2.0, "hectare") in quantities1
    assert (50.0, "kg") in quantities1

    text2 = "3 hektaara fi 100 kuuntaala"
    quantities2 = extract_quantities_oromo(text2)
    assert (3.0, "hectare") in quantities2
    assert (100.0, "quintal") in quantities2
