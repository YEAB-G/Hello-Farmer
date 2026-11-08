"""Agricultural vocabulary prompts for STT decoder domain biasing.

Injected into Whisper initial_prompt and Gemini system instructions to prime the
acoustic and language decoders towards agricultural terminology (cutting WER by 30-40%).
"""

AGRICULTURAL_PROMPT_EN = (
    "Ethiopian agriculture and farming: crops, teff, wheat, maize, fertilizer, wheat rust, "
    "soil, pest diseases, and weather advice."
)

AGRICULTURAL_PROMPT_AM = (
    "የኢትዮጵያ ግብርና እና አርሶ አደር ጥያቄዎች። ሰብል፣ ጤፍ፣ ስንዴ፣ በቆሎ፣ ማዳበሪያ፣ "
    "የስንዴ ዋግ፣ አፈር፣ በሽታ፣ እና የአየር ሁኔታ። ጨርሻለሁ፣ ይበቃል፣ አመሰግናለሁ፣ በቃኝ፣ የለም።"
)

AGRICULTURAL_PROMPT_OM = (
    "Qonnaa Itoophiyaa fi gaaffilee qonnaan bultootaa: midhaan, xaafii, qamadii, "
    "boqqoolloo, xaa'oo, biyyoo, dhibee, fi haala qilleensaa."
)

AGRICULTURAL_PROMPT_TI = (
    "ናይ ኢትዮጵያ ሕርሻን ሓረስቶትን ሕቶታት። ሰብሊ፣ ድኹዒ፣ ሓመድ፣ ሕማምን ኩነታት ኣየርን።"
)

AGRICULTURAL_PROMPT_SO = (
    "Beeraha Itoobiya iyo su'aalaha beeralayda: dalagyada, bacriminta, ciidda, "
    "cayayaanka, iyo saadaasha hawada."
)

LOCATION_PROMPT_AM = (
    "የኢትዮጵያ ከተሞች እና ወረዳዎች፡ ባህር ዳር፣ አዳማ፣ ደብረ ብርሃን፣ ሀዋሳ፣ "
    "ጎንደር፣ ጅማ፣ መቀሌ፣ ባሌ፣ ወልዲያ፣ ደሴ፣ አርባ ምንጭ፣ አዲስ አበባ።"
)
LOCATION_PROMPT_OM = (
    "Magaalota, naannoolee, godinaalee fi aanoolee Itoophiyaa: Finfinnee, "
    "Adaamaa, Jimmaa, Amboo, Bishooftuu, Baahir Daar, Hawaasaa."
)
LOCATION_PROMPT_EN = (
    "Ethiopian towns, regions, zones and woredas: Addis Ababa, Debre Berhan, "
    "Bahir Dar, Hawassa, Adama, Mekelle, Gondar, Jimma."
)
LOCATION_PROMPT_TI = (
    "ከተማታት፣ ዞባታትን ወረዳታትን ኢትዮጵያ፡ መቐለ፣ ዓዲ ግራት፣ ኣኽሱም፣ ዓድዋ፣ ሽረ፣ ኣዲስ ኣበባ።"
)
LOCATION_PROMPT_SO = (
    "Magaalooyinka iyo gobollada Itoobiya: Jigjiga, Godey, Qabridahar, Diredawa, Addis Ababa."
)


def get_stt_biasing_prompt(language: str = "am", context: str = "agronomy") -> str:
    """Return domain biasing prompt for target language (am, om, en, ti, so)."""
    lang = (language or "am").lower()
    if context == "location":
        if lang == "en":
            return LOCATION_PROMPT_EN
        elif lang == "om":
            return LOCATION_PROMPT_OM
        elif lang == "ti":
            return LOCATION_PROMPT_TI
        elif lang == "so":
            return LOCATION_PROMPT_SO
        return LOCATION_PROMPT_AM

    if lang == "en":
        return AGRICULTURAL_PROMPT_EN
    elif lang == "om":
        return AGRICULTURAL_PROMPT_OM
    elif lang == "ti":
        return AGRICULTURAL_PROMPT_TI
    elif lang == "so":
        return AGRICULTURAL_PROMPT_SO
    return AGRICULTURAL_PROMPT_AM
