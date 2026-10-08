"""Warning text generation for SMS and Web notifications in Amharic and Afaan Oromo."""
from dataclasses import dataclass


@dataclass
class LocalizedWarningContent:
    title: str
    description: str
    sms_text: str
    language: str


def generate_rainfall_warning_content(
    location_name: str,
    severity: str,
    rainfall_mm: float,
    language: str = "am",
) -> LocalizedWarningContent:
    """Generate localized title, web description, and SMS text for heavy rainfall."""
    if language == "om":
        title = f"Akeekkachiisa Rooba Cimaa - {location_name} ({severity})"
        if severity in ("HIGH", "CRITICAL"):
            desc = (
                f"Naannoo {location_name}tti roobni cimaan lolaa uumu ({rainfall_mm:.0f} mm) ni eegama. "
                f"Sanyiin fi midhaan akka hin miidhamneef hatattamaan bo'oo lolaa baasaa. "
                f"Horii fi meeshaalee bakka oolmaa eegaa."
            )
            sms = f"Heelo Faarmar: Naannoo {location_name}tti roobni cimaan ni eegama. Hatattamaan bo'oo lolaa baasaa."
        else:
            desc = (
                f"Naannoo {location_name}tti roobni ({rainfall_mm:.0f} mm) ni eegama. "
                f"Bishaan kuullamuun akka hin uumamneef eeggannoo godhaa."
            )
            sms = f"Heelo Faarmar: Naannoo {location_name}tti roobni ni eegama. Maaloo bo'oo lolaa qopheessaa."

    else:  # Amharic default
        title = f"የከባድ ዝናብ ማስጠንቀቂያ - {location_name} ({severity})"
        if severity in ("HIGH", "CRITICAL"):
            desc = (
                f"በ{location_name} አካባቢ ጎርፍ ሊያስከትል የሚችል ከፍተኛ ዝናብ ({rainfall_mm:.0f} ሚሜ) ይጠበቃል። "
                f"ሰብልዎ እንዳይበላሽ በአስቸኳይ የማሳ ውስጥ የውሃ ማስተንፈሻ ቦይ ያውጡ። "
                f"የከብቶች ማደሪያ ደረቅ መሆኑን ያረጋግጡ።"
            )
            sms = f"ሄሎ ፋርመር፡ በ{location_name} ከባድ ዝናብ ስለሚጠበቅ ሰብልዎ እንዳይጥለቀለቅ የማሳ ቦይ ያዘጋጁ።"
        else:
            desc = (
                f"በ{location_name} አካባቢ መጠነኛ እስከ ከፍተኛ ዝናብ ({rainfall_mm:.0f} ሚሜ) ይጠበቃል። "
                f"የውሃ ማቆር ችግር እንዳይከሰት ማሳዎን ይከታተሉ።"
            )
            sms = f"ሄሎ ፋርመር፡ በ{location_name} ዝናብ ስለሚጠበቅ የውሃ ማቆር እንዳይፈጠር ጥንቃቄ ያድርጉ።"

    return LocalizedWarningContent(
        title=title,
        description=desc,
        sms_text=sms,
        language=language,
    )
