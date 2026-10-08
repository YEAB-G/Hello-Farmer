"""SMS text encoding, segment counting, and safe truncation for Amharic & Latin text.

Specifications:
- GSM-7: Standard Latin alphanumeric and basic punctuation (160 chars/single, 153 chars/concat).
- UCS-2: Unicode encoding required for Ethiopic (Ge'ez) script (70 chars/single, 67 chars/concat).
- Safe truncation prevents splitting words or exceeding segment limits.
"""
from dataclasses import dataclass

# Standard GSM-7 character set
GSM7_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`¿abcdefghijklmnopqrstuvwxyzäöñüà"
)


@dataclass
class SMSEncodingResult:
    encoding: str  # 'GSM-7' or 'UCS-2'
    char_count: int
    segment_count: int
    text: str
    is_truncated: bool


def is_gsm7(text: str) -> bool:
    """Check if all characters in text belong to the standard GSM-7 basic charset."""
    return all(ch in GSM7_BASIC for ch in text)


def get_segment_limits(encoding: str) -> tuple[int, int]:
    """Return (single_segment_max, concat_segment_max) for the given encoding."""
    if encoding == "GSM-7":
        return 160, 153
    return 70, 67  # UCS-2 for Ethiopic (Ge'ez) and unicode


def calculate_segments(text: str, encoding: str) -> int:
    """Calculate the number of SMS segments required for text."""
    length = len(text)
    if length == 0:
        return 1

    single_limit, concat_limit = get_segment_limits(encoding)
    if length <= single_limit:
        return 1

    # In concatenated SMS, each segment has a user-data header taking up bytes
    segments = (length + concat_limit - 1) // concat_limit
    return segments


def encode_and_truncate_sms(text: str, max_segments: int = 2) -> SMSEncodingResult:
    """Analyze SMS encoding, calculate segment count, and safely truncate to max_segments."""
    cleaned = text.strip()
    encoding = "GSM-7" if is_gsm7(cleaned) else "UCS-2"

    single_limit, concat_limit = get_segment_limits(encoding)
    max_allowed_chars = single_limit if max_segments == 1 else (max_segments * concat_limit)

    is_truncated = False
    safe_text = cleaned

    if len(cleaned) > max_allowed_chars:
        is_truncated = True
        # Truncate at nearest word boundary before max_allowed_chars - 3 (for ellipsis)
        cutoff = max_allowed_chars - 3
        space_idx = cleaned.rfind(" ", 0, cutoff)
        geez_wordspace_idx = cleaned.rfind("፡", 0, cutoff)
        best_boundary = max(space_idx, geez_wordspace_idx)

        if best_boundary > int(cutoff * 0.7):
            safe_text = cleaned[:best_boundary] + "..."
        else:
            safe_text = cleaned[:cutoff] + "..."

    seg_count = calculate_segments(safe_text, encoding)

    return SMSEncodingResult(
        encoding=encoding,
        char_count=len(safe_text),
        segment_count=seg_count,
        text=safe_text,
        is_truncated=is_truncated,
    )
