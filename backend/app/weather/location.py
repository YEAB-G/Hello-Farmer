"""Place-name directory and fuzzy location resolution for Ethiopian agricultural regions.

Supports structured geocoding, multi-lingual aliases (Amharic, Afaan Oromo, English),
spoken prefix/suffix cleaning, ambiguity detection, and agroecological zone mapping.
"""
import difflib
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LocationMatch:
    name: str
    name_am: str
    name_om: str
    region: str
    zone: str | None
    woreda: str | None
    latitude: float
    longitude: float
    confidence: float
    agroecological_zone: str = "Midland"  # Highland (Dega), Midland (Weyna Dega), Lowland (Kolla)
    resolution_source: str = "Exact_Match"
    country: str = "Ethiopia"
    town: str | None = None
    is_ambiguous: bool = False
    ambiguous_regions: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.town and self.resolution_source != "Regional_State_Match":
            self.town = self.name


# Curated agricultural reference hubs across Ethiopia (high agricultural activity)
DEFAULT_ETHIOPIAN_PLACES = [
    # Oromia
    {
        "name": "Adama",
        "name_am": "አዳማ",
        "name_om": "Adaamaa",
        "aliases": "Nazret,Nazreth,ናዝሬት,adama",
        "region": "Oromia",
        "zone": "East Shewa",
        "woreda": "Adama",
        "latitude": 8.54,
        "longitude": 39.27,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Bishoftu",
        "name_am": "ቢሾፍቱ",
        "name_om": "Bishooftuu",
        "aliases": "Debre Zeit,ደብረ ዘይት,Debrezeit,debre zeyit",
        "region": "Oromia",
        "zone": "East Shewa",
        "woreda": "Bishoftu",
        "latitude": 8.75,
        "longitude": 38.98,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Asella",
        "name_am": "አሰላ",
        "name_om": "Asallaa",
        "aliases": "Asela,አሴላ,asella",
        "region": "Oromia",
        "zone": "Arsi",
        "woreda": "Tiyo",
        "latitude": 7.96,
        "longitude": 39.12,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Ambo",
        "name_am": "አምቦ",
        "name_om": "Amboo",
        "aliases": "Hagere Hiwot,ambo",
        "region": "Oromia",
        "zone": "West Shewa",
        "woreda": "Ambo",
        "latitude": 8.98,
        "longitude": 37.85,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Jimma",
        "name_am": "ጅማ",
        "name_om": "Jimma",
        "aliases": "Jima,ጂማ,jimma",
        "region": "Oromia",
        "zone": "Jimma",
        "woreda": "Jimma",
        "latitude": 7.67,
        "longitude": 36.83,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Bale Robe",
        "name_am": "ሮቤ",
        "name_om": "Roobee",
        "aliases": "Robe,ሮቤ ባሌ,Baale Roobee,bale robe",
        "region": "Oromia",
        "zone": "Bale",
        "woreda": "Sinana",
        "latitude": 7.01,
        "longitude": 40.00,
        "agroecological_zone": "Highland",
        "is_ambiguous": True,
        "ambiguous_regions": ["Oromia", "Arsi"],
    },
    {
        "name": "Nekemte",
        "name_am": "ነቀምቴ",
        "name_om": "Naqamtee",
        "aliases": "Naqamte,ነቀምት,nekemte",
        "region": "Oromia",
        "zone": "East Wollega",
        "woreda": "Nekemte",
        "latitude": 9.08,
        "longitude": 36.55,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Shashamane",
        "name_am": "ሻሸመኔ",
        "name_om": "Shaashamannee",
        "aliases": "Shashemene,ሻሻመኔ,shashamane",
        "region": "Oromia",
        "zone": "West Arsi",
        "woreda": "Shashamane",
        "latitude": 7.20,
        "longitude": 38.60,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Bako",
        "name_am": "ባኮ",
        "name_om": "Baqqoo",
        "aliases": "Bako Tibe,ባኮ ጥቤ,bako",
        "region": "Oromia",
        "zone": "West Shewa",
        "woreda": "Bako Tibe",
        "latitude": 9.12,
        "longitude": 37.05,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Kulumsa",
        "name_am": "ኩሉምሳ",
        "name_om": "Kulumsaa",
        "aliases": "ኩሉምሳ ምርምር ጣቢያ,kulumsa",
        "region": "Oromia",
        "zone": "Arsi",
        "woreda": "Tiyo",
        "latitude": 8.02,
        "longitude": 39.16,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Holeta",
        "name_am": "ሆለታ",
        "name_om": "Hoolotaa",
        "aliases": "Holata,ሆለታ ምርምር,holeta",
        "region": "Oromia",
        "zone": "Oromia Special Zone",
        "woreda": "Walmara",
        "latitude": 9.05,
        "longitude": 38.50,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Fiche",
        "name_am": "ፍቼ",
        "name_om": "Fiichee",
        "aliases": "Fitche,ፍቼ ከተማ,fiche",
        "region": "Oromia",
        "zone": "North Shewa",
        "woreda": "Girba",
        "latitude": 9.80,
        "longitude": 38.73,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Dodola",
        "name_am": "ዶዶላ",
        "name_om": "Doddolaa",
        "aliases": "dodola",
        "region": "Oromia",
        "zone": "West Arsi",
        "woreda": "Dodola",
        "latitude": 6.98,
        "longitude": 39.18,
        "agroecological_zone": "Highland",
    },

    # Amhara
    {
        "name": "Debre Birhan",
        "name_am": "ደብረ ብርሃን",
        "name_om": "Dabra Birhaan",
        "aliases": "Debre Berhan,ደብረብርሃን,debre birhan",
        "region": "Amhara",
        "zone": "North Shewa",
        "woreda": "Debre Birhan",
        "latitude": 9.68,
        "longitude": 39.53,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Bahir Dar",
        "name_am": "ባሕር ዳር",
        "name_om": "Baahir Daar",
        "aliases": "Bahirdar,ባህር ዳር,ባህርዳር,ባሕርዳር,ባሕር ዳር,ህርዳር,በህርዳር,bahir dar,bahirdar,bahidaar,bahidar,bahi daaar,bahr dar,ባሂር ዳር,ባርዳር,ባርዳ,ባር ዳር",
        "region": "Amhara",
        "zone": "West Gojjam",
        "woreda": "Bahir Dar",
        "latitude": 11.59,
        "longitude": 37.39,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Gondar",
        "name_am": "ጎንደር",
        "name_om": "Gondar",
        "aliases": "Gonder,ጎንደር ከተማ,gondar",
        "region": "Amhara",
        "zone": "Central Gondar",
        "woreda": "Gondar",
        "latitude": 12.60,
        "longitude": 37.47,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Dessie",
        "name_am": "ደሴ",
        "name_om": "Dasee",
        "aliases": "Dese,ዴሴ,ደሴ ከተማ,dessie",
        "region": "Amhara",
        "zone": "South Wollo",
        "woreda": "Dessie",
        "latitude": 11.13,
        "longitude": 39.63,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Debre Markos",
        "name_am": "ደብረ ማርቆስ",
        "name_om": "Dabra Maarqos",
        "aliases": "Debre Marcos,ደብረማርቆስ,debre markos",
        "region": "Amhara",
        "zone": "East Gojjam",
        "woreda": "Debre Markos",
        "latitude": 10.33,
        "longitude": 37.73,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Kombolcha",
        "name_am": "ኮምቦልቻ",
        "name_om": "Kombolcha",
        "aliases": "ኮምቦልቻ ከተማ,kombolcha",
        "region": "Amhara",
        "zone": "South Wollo",
        "woreda": "Kombolcha",
        "latitude": 11.08,
        "longitude": 39.73,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Debre Tabor",
        "name_am": "ደብረ ታቦር",
        "name_om": "Dabra Taaboor",
        "aliases": "ደብረታቦር,debre tabor",
        "region": "Amhara",
        "zone": "South Gondar",
        "woreda": "Debre Tabor",
        "latitude": 11.85,
        "longitude": 38.02,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Kobo",
        "name_am": "ቆቦ",
        "name_om": "Qobboo",
        "aliases": "Kobo,ቆቦ ራያ,ራያ ቆቦ",
        "region": "Amhara",
        "zone": "North Wollo",
        "woreda": "Raya Kobo",
        "latitude": 12.15,
        "longitude": 39.63,
        "agroecological_zone": "Lowland",
    },

    # Tigray
    {
        "name": "Mekelle",
        "name_am": "መቀሌ",
        "name_om": "Maqallee",
        "aliases": "Mekele,መቐለ,mekelle",
        "region": "Tigray",
        "zone": "Mekelle",
        "woreda": "Mekelle",
        "latitude": 13.50,
        "longitude": 39.47,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Shire",
        "name_am": "ሽሬ",
        "name_om": "Shiiree",
        "aliases": "Inda Selassie,ሽሬ እንዳስላሴ,shire",
        "region": "Tigray",
        "zone": "North Western Tigray",
        "woreda": "Shire",
        "latitude": 14.10,
        "longitude": 38.28,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Axum",
        "name_am": "አክሱም",
        "name_om": "Aksum",
        "aliases": "Aksum,አክሱም ከተማ,axum",
        "region": "Tigray",
        "zone": "Central Tigray",
        "woreda": "Axum",
        "latitude": 14.13,
        "longitude": 38.72,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Alamata",
        "name_am": "አላማጣ",
        "name_om": "Alaamaaxaa",
        "aliases": "አለማጣ,alamata",
        "region": "Tigray",
        "zone": "Southern Tigray",
        "woreda": "Alamata",
        "latitude": 12.42,
        "longitude": 39.55,
        "agroecological_zone": "Lowland",
    },

    # Sidama & South Ethiopia / Central Ethiopia
    {
        "name": "Hawassa",
        "name_am": "ሀዋሳ",
        "name_om": "Hawaasaa",
        "aliases": "Awassa,አዋሳ,Awasa,hawassa",
        "region": "Sidama",
        "zone": "Hawassa",
        "woreda": "Hawassa",
        "latitude": 7.05,
        "longitude": 38.47,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Wolaita Sodo",
        "name_am": "ሶዶ",
        "name_om": "Soddoo",
        "aliases": "Sodo,ዎላይታ ሶዶ,Wolayta Sodo,sodo",
        "region": "South Ethiopia",
        "zone": "Wolaita",
        "woreda": "Sodo",
        "latitude": 6.86,
        "longitude": 37.75,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Arba Minch",
        "name_am": "አርባ ምንጭ",
        "name_om": "Arbaa Minxi",
        "aliases": "Arbaminch,አርባምንጭ,arba minch",
        "region": "South Ethiopia",
        "zone": "Gamo",
        "woreda": "Arba Minch",
        "latitude": 6.03,
        "longitude": 37.55,
        "agroecological_zone": "Lowland",
    },
    {
        "name": "Dilla",
        "name_am": "ዲላ",
        "name_om": "Dillaa",
        "aliases": "ዲላ ከተማ,dilla",
        "region": "South Ethiopia",
        "zone": "Gedeo",
        "woreda": "Dilla",
        "latitude": 6.41,
        "longitude": 38.31,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Hossana",
        "name_am": "ሆሳዕና",
        "name_om": "Hosaa'inaa",
        "aliases": "Hosanna,ሆሳና,ሆሳዕና ከተማ,hossana",
        "region": "Central Ethiopia",
        "zone": "Hadiya",
        "woreda": "Hossana",
        "latitude": 7.55,
        "longitude": 37.85,
        "agroecological_zone": "Highland",
    },
    {
        "name": "Butajira",
        "name_am": "ቡታጅራ",
        "name_om": "Buttaajirra",
        "aliases": "ቡታጅራ ከተማ,butajira",
        "region": "Central Ethiopia",
        "zone": "Gurage",
        "woreda": "Meskan",
        "latitude": 8.12,
        "longitude": 38.37,
        "agroecological_zone": "Midland",
    },

    # Eastern, Western & Pastoralist Regions
    {
        "name": "Harar",
        "name_am": "ሐረር",
        "name_om": "Harar",
        "aliases": "Harrar,ሐረርጌ,ሀረር,harar",
        "region": "Harari",
        "zone": "Harari",
        "woreda": "Harar",
        "latitude": 9.31,
        "longitude": 42.12,
        "agroecological_zone": "Midland",
    },
    {
        "name": "Dire Dawa",
        "name_am": "ድሬዳዋ",
        "name_om": "Dirree Dawaa",
        "aliases": "ድሬ ዳዋ,dire dawa",
        "region": "Dire Dawa",
        "zone": "Dire Dawa",
        "woreda": "Dire Dawa",
        "latitude": 9.60,
        "longitude": 41.86,
        "agroecological_zone": "Lowland",
    },
    {
        "name": "Jigjiga",
        "name_am": "ጅግጅጋ",
        "name_om": "Jijiga",
        "aliases": "Jijiga,ጂግጂጋ,jigjiga",
        "region": "Somali",
        "zone": "Fafan",
        "woreda": "Jigjiga",
        "latitude": 9.35,
        "longitude": 42.80,
        "agroecological_zone": "Lowland",
    },
    {
        "name": "Assosa",
        "name_am": "አሶሳ",
        "name_om": "Asosa",
        "aliases": "አሶሳ ከተማ,asosa,assosa",
        "region": "Benishangul-Gumuz",
        "zone": "Assosa",
        "woreda": "Assosa",
        "latitude": 10.07,
        "longitude": 34.53,
        "agroecological_zone": "Lowland",
    },
    {
        "name": "Gambella",
        "name_am": "ጋምቤላ",
        "name_om": "Gambella",
        "aliases": "ጋምቤላ ከተማ,gambella",
        "region": "Gambella",
        "zone": "Anuak",
        "woreda": "Gambella",
        "latitude": 8.25,
        "longitude": 34.58,
        "agroecological_zone": "Lowland",
    },
    {
        "name": "Semera",
        "name_am": "ሰመራ",
        "name_om": "Samara",
        "aliases": "ሰመራ ከተማ,semera",
        "region": "Afar",
        "zone": "Awsi Rasu",
        "woreda": "Dubti",
        "latitude": 11.79,
        "longitude": 41.00,
        "agroecological_zone": "Lowland",
    },
]

# Regional States Mapping for Fallback Context
REGIONAL_STATES = {
    "oromia": {"name_am": "ኦሮሚያ", "name_om": "Oromiyaa", "region": "Oromia", "lat": 8.5, "lon": 39.0},
    "amhara": {"name_am": "አማራ", "name_om": "Amaara", "region": "Amhara", "lat": 11.5, "lon": 38.0},
    "tigray": {"name_am": "ትግራይ", "name_om": "Tigraay", "region": "Tigray", "lat": 13.5, "lon": 39.0},
    "sidama": {"name_am": "ሲዳማ", "name_om": "Sidaama", "region": "Sidama", "lat": 6.8, "lon": 38.5},
    "somali": {"name_am": "ሶማሌ", "name_om": "Somaalee", "region": "Somali", "lat": 7.0, "lon": 44.0},
    "afar": {"name_am": "አፋር", "name_om": "Afaar", "region": "Afar", "lat": 11.5, "lon": 41.0},
    "benishangul": {"name_am": "ቤንሻንጉል", "name_om": "Baniishaangul", "region": "Benishangul-Gumuz", "lat": 10.0, "lon": 35.0},
    "gambella": {"name_am": "ጋምቤላ", "name_om": "Gambeellaa", "region": "Gambella", "lat": 8.2, "lon": 34.5},
    "harari": {"name_am": "ሐረሪ", "name_om": "Hararii", "region": "Harari", "lat": 9.3, "lon": 42.1},
    "south ethiopia": {"name_am": "ደቡብ ኢትዮጵያ", "name_om": "Kibba Itoophiyaa", "region": "South Ethiopia", "lat": 6.5, "lon": 37.5},
}


def clean_spoken_location_text(query_text: str) -> str:
    """Strip common spoken conversational prefixes/suffixes from location answers.

    Examples:
      - 'ከአዳማ ነው' -> 'አዳማ'
      - 'ከደብረ ብርሃን' -> 'ደብረ ብርሃን'
      - 'በአሰላ አካባቢ ነው' -> 'አሰላ'
      - 'Adaamaa irraa' -> 'Adaamaa'
      - 'I am calling from Hawassa' -> 'Hawassa'
    """
    text = query_text.strip()
    # Strip Amharic conversational words
    amharic_stop_words = ["ነው", "ነኝ", "እየደወልኩ", "የምደውለው", "አካባቢ", "ከተማ", "ወረዳ", "ዞን"]
    for word in amharic_stop_words:
        text = re.sub(rf"(?:^|\s+){re.escape(word)}(?:\s+|$)", " ", text)

    # Strip English conversational phrases
    text = re.sub(r"\b(i am calling from|from|calling from|nearby|town|city|around|in)\b", " ", text, flags=re.IGNORECASE)
    # Strip Oromo conversational tails
    text = re.sub(r"\b(irraa|keessaa|kanan bilbilu|magaalaa|aanaa)\b", " ", text, flags=re.IGNORECASE)

    # Clean punctuation & excess whitespace
    text = re.sub(r"[^\w\s]", " ", text)
    cleaned = " ".join(text.split()).strip()

    # If word starts with 'ከ' or 'በ' (attached preposition in Ge'ez), strip prefix
    words = cleaned.split()
    processed_words = []
    for w in words:
        if len(w) > 2 and (w.startswith("ከ") or w.startswith("በ")):
            processed_words.append(w[1:])
        else:
            processed_words.append(w)
    return " ".join(processed_words)


def resolve_location(
    query_text: str,
    region_hint: str | None = None,
    threshold: float = 0.60
) -> LocationMatch | None:
    """Resolve a place name from natural language text using exact, alias, and fuzzy matching.

    Never defaults silently to Addis Ababa or an invented location.
    Returns LocationMatch with full structured geography (town, woreda, zone, region, coordinates, agroecology).
    """
    if not query_text or not query_text.strip():
        return None

    cleaned_raw = query_text.lower().strip()
    cleaned_normalized = clean_spoken_location_text(query_text).lower()

    # Search candidates across exact, stripped, and word tokens
    search_texts = [cleaned_raw, cleaned_normalized]
    tokens = re.findall(r"[\w]+", cleaned_normalized)

    # 1. Exact & Alias Matches
    matches_found: list[tuple[dict, float, str]] = []

    for place in DEFAULT_ETHIOPIAN_PLACES:
        candidates = [
            (place["name"].lower(), "exact_name"),
            (place["name_am"].lower(), "exact_amharic"),
            (place["name_om"].lower(), "exact_oromo"),
        ]
        if place.get("aliases"):
            for a in place["aliases"].split(","):
                cand_clean = a.strip().lower()
                if cand_clean:
                    candidates.append((cand_clean, "alias"))

        for cand, match_type in candidates:
            for s_text in search_texts:
                # Substring check with word boundaries or direct inclusion
                if cand in s_text:
                    score = 1.0 if match_type != "alias" else 0.95
                    # Region hint match boost
                    if region_hint and region_hint.lower() in place["region"].lower():
                        score += 0.05
                    matches_found.append((place, score, match_type))
                    break

    if matches_found:
        # Sort by score descending
        matches_found.sort(key=lambda x: x[1], reverse=True)
        best_place, score, source_type = matches_found[0]

        # Check for ambiguity if more than one place matched differently
        distinct_regions = {p["region"] for p, _, _ in matches_found}
        is_ambig = len(distinct_regions) > 1 and not region_hint

        return LocationMatch(
            name=best_place["name"],
            name_am=best_place["name_am"],
            name_om=best_place["name_om"],
            town=best_place["name"],
            region=best_place["region"],
            zone=best_place.get("zone"),
            woreda=best_place.get("woreda"),
            latitude=best_place["latitude"],
            longitude=best_place["longitude"],
            confidence=round(score, 2),
            agroecological_zone=best_place.get("agroecological_zone", "Midland"),
            resolution_source=source_type,
            is_ambiguous=is_ambig or best_place.get("is_ambiguous", False),
            ambiguous_regions=list(distinct_regions) if is_ambig else best_place.get("ambiguous_regions", []),
        )

    # 2. Fuzzy Matching across individual tokens
    best_match = None
    best_score = 0.0

    for place in DEFAULT_ETHIOPIAN_PLACES:
        candidates = [place["name"].lower(), place["name_am"].lower(), place["name_om"].lower()]
        if place.get("aliases"):
            candidates.extend([a.strip().lower() for a in place["aliases"].split(",") if a.strip()])

        for token in tokens:
            if len(token) < 3:
                continue
            for cand in candidates:
                sim = difflib.SequenceMatcher(None, token, cand).ratio()
                if sim > best_score:
                    best_score = sim
                    best_match = place

    if best_match and best_score >= threshold:
        return LocationMatch(
            name=best_match["name"],
            name_am=best_match["name_am"],
            name_om=best_match["name_om"],
            town=best_match["name"],
            region=best_match["region"],
            zone=best_match.get("zone"),
            woreda=best_match.get("woreda"),
            latitude=best_match["latitude"],
            longitude=best_match["longitude"],
            confidence=round(best_score, 2),
            agroecological_zone=best_match.get("agroecological_zone", "Midland"),
            resolution_source="Fuzzy_Match",
        )

    # 3. Check for Regional State mentions as general location (Never silent default)
    for reg_key, reg_info in REGIONAL_STATES.items():
        if (
            reg_key in cleaned_raw
            or reg_info["name_am"] in cleaned_raw
            or reg_info["name_om"].lower() in cleaned_raw
        ):
            return LocationMatch(
                name=f"{reg_info['region']} Region",
                name_am=f"{reg_info['name_am']} ክልል",
                name_om=f"Naannoo {reg_info['name_om']}",
                town=None,
                region=reg_info["region"],
                zone=None,
                woreda=None,
                latitude=reg_info["lat"],
                longitude=reg_info["lon"],
                confidence=0.75,
                agroecological_zone="Regional_General",
                resolution_source="Regional_State_Match",
            )

    return None


def format_spoken_location_confirmation(location: LocationMatch, language: str = "am") -> str:
    """Produce a natural spoken confirmation string for the location."""
    if language == "om":
        return f"Naannoo {location.name_om}tti"
    elif language == "en":
        return f"In the {location.name} area,"
    return f"በ{location.name_am} አካባቢ"


async def seed_place_names_if_empty() -> int:
    """Populate database place_names table with reference places if currently empty."""
    from sqlalchemy import select

    from app.database.models import PlaceName
    from app.database.session import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(select(PlaceName).limit(1))
        if result.scalar_one_or_none() is not None:
            return 0  # Already seeded

        count = 0
        for p in DEFAULT_ETHIOPIAN_PLACES:
            place_obj = PlaceName(
                name=p["name"],
                name_am=p["name_am"],
                name_om=p["name_om"],
                aliases=p.get("aliases"),
                region=p["region"],
                zone=p.get("zone"),
                woreda=p.get("woreda"),
                latitude=p["latitude"],
                longitude=p["longitude"],
                provenance="EIAR_CSA_Reference",
            )
            session.add(place_obj)
            count += 1
        await session.commit()
        logger.info(f"Seeded {count} place names into PostgreSQL")
        return count
