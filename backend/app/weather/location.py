"""Place-name directory and fuzzy location resolution for Ethiopian agricultural regions."""
import difflib
import logging
import re
from dataclasses import dataclass

from app.database.models import PlaceName
from app.database.session import async_session_factory

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


# Curated agricultural reference hubs across Ethiopia (high agricultural activity)
DEFAULT_ETHIOPIAN_PLACES = [
    {
        "name": "Adama",
        "name_am": "አዳማ",
        "name_om": "Adaamaa",
        "aliases": "Nazret,Nazreth,ናዝሬት",
        "region": "Oromia",
        "zone": "East Shewa",
        "woreda": "Adama",
        "latitude": 8.54,
        "longitude": 39.27,
    },
    {
        "name": "Bishoftu",
        "name_am": "ቢሾፍቱ",
        "name_om": "Bishooftuu",
        "aliases": "Debre Zeit,ደብረ ዘይት,Debrezeit",
        "region": "Oromia",
        "zone": "East Shewa",
        "woreda": "Bishoftu",
        "latitude": 8.75,
        "longitude": 38.98,
    },
    {
        "name": "Asella",
        "name_am": "አሰላ",
        "name_om": "Asallaa",
        "aliases": "Asela,አሴላ",
        "region": "Oromia",
        "zone": "Arsi",
        "woreda": "Tiyo",
        "latitude": 7.96,
        "longitude": 39.12,
    },
    {
        "name": "Ambo",
        "name_am": "አምቦ",
        "name_om": "Amboo",
        "aliases": "Hagere Hiwot",
        "region": "Oromia",
        "zone": "West Shewa",
        "woreda": "Ambo",
        "latitude": 8.98,
        "longitude": 37.85,
    },
    {
        "name": "Hawassa",
        "name_am": "ሀዋሳ",
        "name_om": "Hawaasaa",
        "aliases": "Awassa,አዋሳ,Awasa",
        "region": "Sidama",
        "zone": "Hawassa",
        "woreda": "Hawassa",
        "latitude": 7.05,
        "longitude": 38.47,
    },
    {
        "name": "Jimma",
        "name_am": "ጅማ",
        "name_om": "Jimma",
        "aliases": "Jima,ጂማ",
        "region": "Oromia",
        "zone": "Jimma",
        "woreda": "Jimma",
        "latitude": 7.67,
        "longitude": 36.83,
    },
    {
        "name": "Bale Robe",
        "name_am": "ሮቤ",
        "name_om": "Roobee",
        "aliases": "Robe,ሮቤ ባሌ,Baale Roobee",
        "region": "Oromia",
        "zone": "Bale",
        "woreda": "Sinana",
        "latitude": 7.01,
        "longitude": 40.00,
    },
    {
        "name": "Debre Birhan",
        "name_am": "ደብረ ብርሃን",
        "name_om": "Dabra Birhaan",
        "aliases": "Debre Berhan,ደብረብርሃን",
        "region": "Amhara",
        "zone": "North Shewa",
        "woreda": "Debre Birhan",
        "latitude": 9.68,
        "longitude": 39.53,
    },
    {
        "name": "Bahir Dar",
        "name_am": "ባሕር ዳር",
        "name_om": "Baahir Daar",
        "aliases": "Bahirdar,ባህር ዳር,ባህርዳር",
        "region": "Amhara",
        "zone": "West Gojjam",
        "woreda": "Bahir Dar",
        "latitude": 11.59,
        "longitude": 37.39,
    },
    {
        "name": "Gondar",
        "name_am": "ጎንደር",
        "name_om": "Gondar",
        "aliases": "Gonder,ጎንደር ከተማ",
        "region": "Amhara",
        "zone": "Central Gondar",
        "woreda": "Gondar",
        "latitude": 12.60,
        "longitude": 37.47,
    },
    {
        "name": "Dessie",
        "name_am": "ደሴ",
        "name_om": "Dasee",
        "aliases": "Dese,ዴሴ",
        "region": "Amhara",
        "zone": "South Wollo",
        "woreda": "Dessie",
        "latitude": 11.13,
        "longitude": 39.63,
    },
    {
        "name": "Wolaita Sodo",
        "name_am": "ሶዶ",
        "name_om": "Soddoo",
        "aliases": "Sodo,ዎላይታ ሶዶ,Wolayta Sodo",
        "region": "South Ethiopia",
        "zone": "Wolaita",
        "woreda": "Sodo",
        "latitude": 6.86,
        "longitude": 37.75,
    },
    {
        "name": "Nekemte",
        "name_am": "ነቀምቴ",
        "name_om": "Naqamtee",
        "aliases": "Naqamte,ነቀምት",
        "region": "Oromia",
        "zone": "East Wollega",
        "woreda": "Nekemte",
        "latitude": 9.08,
        "longitude": 36.55,
    },
    {
        "name": "Shashamane",
        "name_am": "ሻሸመኔ",
        "name_om": "Shaashamannee",
        "aliases": "Shashemene,ሻሻመኔ",
        "region": "Oromia",
        "zone": "West Arsi",
        "woreda": "Shashamane",
        "latitude": 7.20,
        "longitude": 38.60,
    },
    {
        "name": "Harar",
        "name_am": "ሐረር",
        "name_om": "Harar",
        "aliases": "Harrar,ሐረርጌ,ሀረር",
        "region": "Harari",
        "zone": "Harari",
        "woreda": "Harar",
        "latitude": 9.31,
        "longitude": 42.12,
    },
    {
        "name": "Bako",
        "name_am": "ባኮ",
        "name_om": "Baqqoo",
        "aliases": "Bako Tibe,ባኮ ጥቤ",
        "region": "Oromia",
        "zone": "West Shewa",
        "woreda": "Bako Tibe",
        "latitude": 9.12,
        "longitude": 37.05,
    },
    {
        "name": "Kulumsa",
        "name_am": "ኩሉምሳ",
        "name_om": "Kulumsaa",
        "aliases": "ኩሉምሳ ምርምር ጣቢያ",
        "region": "Oromia",
        "zone": "Arsi",
        "woreda": "Tiyo",
        "latitude": 8.02,
        "longitude": 39.16,
    },
    {
        "name": "Holeta",
        "name_am": "ሆለታ",
        "name_om": "Hoolotaa",
        "aliases": "Holata,ሆለታ ምርምር",
        "region": "Oromia",
        "zone": "Oromia Special Zone",
        "woreda": "Walmara",
        "latitude": 9.05,
        "longitude": 38.50,
    },
]


def resolve_location(query_text: str, threshold: float = 0.60) -> LocationMatch | None:
    """Resolve a place name from a natural language string using exact & fuzzy matching."""
    if not query_text or not query_text.strip():
        return None

    cleaned_query = query_text.lower().strip()
    words = re.findall(r"[\w]+", cleaned_query)

    best_match = None
    best_score = 0.0

    for place in DEFAULT_ETHIOPIAN_PLACES:
        candidates = [
            place["name"].lower(),
            place["name_am"].lower(),
            place["name_om"].lower(),
        ]
        if place.get("aliases"):
            candidates.extend([a.strip().lower() for a in place["aliases"].split(",")])

        # 1. Exact substring check in full query
        for cand in candidates:
            if cand in cleaned_query:
                # Direct match found
                return LocationMatch(
                    name=place["name"],
                    name_am=place["name_am"],
                    name_om=place["name_om"],
                    region=place["region"],
                    zone=place.get("zone"),
                    woreda=place.get("woreda"),
                    latitude=place["latitude"],
                    longitude=place["longitude"],
                    confidence=1.0,
                )

        # 2. Fuzzy match word by word
        for word in words:
            for cand in candidates:
                sim = difflib.SequenceMatcher(None, word, cand).ratio()
                if sim > best_score:
                    best_score = sim
                    best_match = place

    if best_match and best_score >= threshold:
        return LocationMatch(
            name=best_match["name"],
            name_am=best_match["name_am"],
            name_om=best_match["name_om"],
            region=best_match["region"],
            zone=best_match.get("zone"),
            woreda=best_match.get("woreda"),
            latitude=best_match["latitude"],
            longitude=best_match["longitude"],
            confidence=round(best_score, 2),
        )

    return None


def format_spoken_location_confirmation(location: LocationMatch, language: str = "am") -> str:
    """Produce a natural spoken confirmation string for the location."""
    if language == "om":
        return f"Naannoo {location.name_om}tti"
    return f"በ{location.name_am} አካባቢ"


async def seed_place_names_if_empty() -> int:
    """Populate database place_names table with reference places if currently empty."""
    from sqlalchemy import select

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
