"""Farmer Context and Agronomic Attribute Extraction from Spoken Transcripts.

Extracts:
- Crop (Teff, Maize, Wheat, Barley, Sorghum, Coffee, etc.)
- Symptoms (Yellowing leaves, spots, rust, wilting, moisture stress)
- Growth stage (Seedling, tillering, flowering, grain filling, maturity)
- Location mentions (Adama, Bishoftu, Arsi, Ambo, etc.)
"""
import re
from typing import Any

from pydantic import BaseModel

CROP_KEYWORDS = {
    "teff": ["ጤፍ", "xaafii", "teff", "ጣፍ"],
    "maize": ["በቆሎ", "boqqoolloo", "maize", "corn"],
    "wheat": ["ስንዴ", "qamadii", "wheat"],
    "barley": ["ገብስ", "garbuu", "barley"],
    "sorghum": ["ማሽላ", "mishingaa", "sorghum"],
    "coffee": ["ቡና", "buna", "coffee"],
    "faba_bean": ["ባቄላ", "baaqelaa", "faba bean", "broad bean"],
}

SYMPTOM_KEYWORDS = {
    "yellowing_leaves": ["ቢጫ", "keelloo", "yellow", "ቢጫ ቅጠል", "baala keelloo"],
    "leaf_spots": ["ነጠብጣብ", "ቡናማ ነጠብጣብ", "mallattoo", "spots", "blight"],
    "rust": ["ዋግ", "ቢጫ ዋግ", "waagii", "rust", "pustules"],
    "waterlogging": ["ውሃ ማቆር", "ውሃ ተኝቷል", "bishaan kuullamuu", "waterlogged", "drainage"],
    "wilting": ["መድረቅ", "መጠውለግ", "goguu", "wilting"],
    "insects_pests": ["ተባይ", "ትል", "ስራፊ", "ilbiisa", "armyworm", "caterpillar"],
}

STAGE_KEYWORDS = {
    "seedling": ["ቡቃያ", "መብቀል", "biqila", "seedling", "germination"],
    "tillering": ["ማፍራት", "መከፋፈል", "tillering", "vegetative"],
    "flowering": ["ማበብ", "አበባ", "daraaraa", "flowering"],
    "grain_filling": ["ፍሬ መያዝ", "ፍሬ", "midhaan", "grain filling"],
    "maturity": ["መብሰል", "መድረስ", "bilchaachuu", "mature", "harvest"],
}

LOCATION_KEYWORDS = {
    "Adama": ["አዳማ", "adama", "nazret", "ናዝሬት"],
    "Bishoftu": ["ቢሾፍቱ", "ደብረ ዘይት", "bishoftu", "debre zeit"],
    "Arsi": ["አርሲ", "arsi", "asella", "አሰላ"],
    "Ambo": ["አምቦ", "ambo"],
    "Hawassa": ["ሀዋሳ", "hawassa", "awassa"],
    "Bale": ["ባሌ", "baale", "bale", "roba", "ሮቤ"],
    "Debre Birhan": ["ደብረ ብርሃን", "debre birhan"],
    "Bahr Dar": ["ባህር ዳር", "bahir dar"],
}


class ExtractedFarmerContext(BaseModel):
    crop: str | None = None
    crop_raw: str | None = None
    symptoms: list[str] = []
    growth_stage: str | None = None
    location: str | None = None
    detected_language: str | None = None


def extract_context_from_utterance(text: str, language: str = "am") -> ExtractedFarmerContext:
    """Extract structured agricultural attributes from user query text."""
    clean_text = text.lower().strip()
    result = ExtractedFarmerContext(detected_language=language)

    # 1. Crop Extraction
    for crop_id, aliases in CROP_KEYWORDS.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", clean_text) or alias in clean_text:
                result.crop = crop_id
                result.crop_raw = alias
                break
        if result.crop:
            break

    # 2. Symptoms Extraction
    for symptom_id, aliases in SYMPTOM_KEYWORDS.items():
        for alias in aliases:
            if alias in clean_text:
                result.symptoms.append(symptom_id)
                break

    # 3. Growth Stage Extraction
    for stage_id, aliases in STAGE_KEYWORDS.items():
        for alias in aliases:
            if alias in clean_text:
                result.growth_stage = stage_id
                break
        if result.growth_stage:
            break

    # 4. Location Extraction
    for loc_name, aliases in LOCATION_KEYWORDS.items():
        for alias in aliases:
            if alias in clean_text:
                result.location = loc_name
                break
        if result.location:
            break

    return result


def merge_farmer_context(
    existing: dict[str, Any],
    new_extracted: ExtractedFarmerContext
) -> dict[str, Any]:
    """Merge newly extracted turn context into ongoing conversation state."""
    merged = dict(existing)
    if new_extracted.crop:
        merged["crop"] = new_extracted.crop
    if new_extracted.symptoms:
        prior_symptoms = set(merged.get("symptoms", []))
        prior_symptoms.update(new_extracted.symptoms)
        merged["symptoms"] = list(prior_symptoms)
    if new_extracted.growth_stage:
        merged["growth_stage"] = new_extracted.growth_stage
    if new_extracted.location:
        merged["location"] = new_extracted.location
    return merged
