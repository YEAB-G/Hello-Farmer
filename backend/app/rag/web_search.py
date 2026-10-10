"""Live Web & Internet Search Engine for Agricultural Knowledge.

Searches the internet for real-time agricultural advisories, pest management,
soil fertility, crop guides, and weather recommendations.
"""
import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger("hello_farmer.rag.web_search")

# User agent for web requests
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def search_duckduckgo_lite(query: str, max_results: int = 4) -> list[dict[str, str]]:
    """Search DuckDuckGo Lite endpoint for clean HTML snippets."""
    url = "https://lite.duckduckgo.com/lite/"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    data = {"q": query}

    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.post(url, data=data, headers=headers)
            if resp.status_code != 200:
                logger.warning("DuckDuckGo Lite returned status %d", resp.status_code)
                return []

            html = resp.text
            # Parse result-snippet
            snippets = re.findall(
                r"<td[^>]*class=[\"']result-snippet[\"'][^>]*>(.*?)</td>",
                html,
                re.DOTALL | re.IGNORECASE,
            )
            # Parse links / titles
            titles = re.findall(
                r"<a[^>]*class=[\"']result-link[\"'][^>]*>(.*?)</a>",
                html,
                re.DOTALL | re.IGNORECASE,
            )

            results = []
            for i in range(min(len(snippets), max_results)):
                clean_snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()
                clean_title = (
                    re.sub(r"<[^>]+>", "", titles[i]).strip()
                    if i < len(titles)
                    else f"Agricultural Web Result {i+1}"
                )
                if clean_snippet:
                    results.append({"title": clean_title, "snippet": clean_snippet})
            return results
    except Exception as e:
        logger.warning("DuckDuckGo Lite search error: %s", e)
        return []


async def search_wikipedia(query: str, lang: str = "en", max_results: int = 2) -> list[dict[str, str]]:
    """Search Wikipedia API for agricultural concepts and pests."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": max_results,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data.get("query", {}).get("search", [])
            results = []
            for item in items:
                title = item.get("title", "")
                snippet = re.sub(r"<[^>]+>", "", item.get("snippet", "")).strip()
                if snippet:
                    results.append({"title": f"Wikipedia: {title}", "snippet": snippet})
            return results
    except Exception as e:
        logger.warning("Wikipedia search error: %s", e)
        return []


AGRICULTURAL_KEYWORDS = {
    "agriculture", "farming", "crop", "crops", "pest", "pests", "soil", "farmer",
    "farmers", "yield", "disease", "fertilizer", "teff", "wheat", "maize", "fungicide",
    "pesticide", "seed", "plant", "planting", "armyworm", "rust", "weather", "spray",
    "potato", "tomato", "onion", "garlic", "barley", "sorghum", "coffee", "bean",
    "ማዳበሪያ", "ሰብል", "እርሻ", "በሽታ", "ተባይ", "ምርት", "ጤፍ", "ስንዴ", "በቆሎ", "አፈር", "ኬሚካል", "ዝናብ",
    "ድንች", "ቲማቲም", "ሽንኩርት", "ገብስ", "ማሽላ", "ቡና", "ባቄላ", "አተር", "ዘር", "ውሃ",
    "qamadii", "xaafii", "boqqoolloo", "xaa'oo", "hoomaa", "rooba", "dinicha", "garbuu", "buna"
}

JUNK_KEYWORDS = {
    "youtube", "ቀሚስ", "ሙዚቃ", "ፊልም", "ዜና", "ቪዲዮ", "አየር መንገድ", "ሰበር", "መዝሙር",
    "ቤተክርስቲያን", "song", "video", "airline", "dress", "fashion", "wedding", "qophii", "drama"
}

# Mapping of Ethiopian agricultural terms (Amharic & Afaan Oromo) to English search keywords
ETHIO_AGRI_TERM_MAP = {
    # Major Crops
    "ጤፍ": "teff agronomy",
    "xaafii": "teff agronomy",
    "ስንዴ": "wheat production",
    "qamadii": "wheat production",
    "በቆሎ": "maize corn production",
    "boqqoolloo": "maize corn production",
    "ገብስ": "barley farming",
    "garbuu": "barley farming",
    "ማሽላ": "sorghum cultivation",
    "misingaa": "sorghum cultivation",
    "ቡና": "coffee arabica management",
    "buna": "coffee management",
    "ድንች": "potato cultivation disease",
    "dinicha": "potato cultivation disease",
    "ቲማቲም": "tomato blight pest control",
    "timaatima": "tomato pest management",
    "ሽንኩርት": "onion garlic farming",
    "qullubbii": "onion garlic farming",
    "ባቄላ": "faba bean disease management",
    "baaqelaa": "faba bean management",
    "አተር": "field pea farming",
    "atara": "field pea farming",
    "አኩሪ አተር": "soybean cultivation",
    "soyaa": "soybean cultivation",
    "ጎመን": "cabbage kale pests",
    "raafuu": "cabbage pests",
    "በርበሬ": "pepper chili disease",
    "barbaree": "pepper chili disease",
    "እንስሳት": "livestock cattle feed",
    "beeylada": "livestock feed",
    "ላም": "dairy cow health feed",
    "sa'a": "dairy cow feed",
    "ዶሮ": "poultry chicken disease",
    "lukkuu": "poultry chicken disease",
    "ወተት": "dairy milk production",

    # Farming Operations & Problems
    "ተምች": "fall armyworm pest control maize",
    "ትል": "stem borer caterpillar pest control",
    "ተባይ": "pest insect infestation control advisory",
    "ነቀዝ": "grain weevil storage pest management",
    "ilbiisa": "pest insect infestation control",
    "raammoo": "armyworm caterpillar control",
    "ዋግ": "stripe yellow stem rust fungicide wheat",
    "waagii": "wheat rust fungal disease",
    "በሽታ": "crop disease management symptoms",
    "dhibee": "crop disease management",
    "dhukkuba": "crop disease control",
    "መበስበስ": "rot blight fungal disease",
    "ማዳበሪያ": "fertilizer NPS Urea application rate Ethiopia",
    "xaa'oo": "fertilizer NPS Urea application rate",
    "ዩሪያ": "Urea nitrogen fertilizer application rate",
    "yuriyaa": "Urea fertilizer rate",
    "ኤንፒኤስ": "NPS fertilizer rate Ethiopia crops",
    "ዳፕ": "DAP phosphate fertilizer Ethiopia",
    "ኮምፖስት": "compost organic manure preparation soil",
    "kompoostii": "compost organic manure soil",
    "ዘር": "seed rate planting spacing",
    "sanyii": "seed rate planting spacing",
    "መዝራት": "planting sowing season time calendar Ethiopia",
    "facaasuu": "planting sowing season time Ethiopia",
    "አረም": "weed weeding management herbicide",
    "aramaa": "weed control management",
    "ውሃ": "irrigation water requirement drought",
    "bishaan": "irrigation water requirement",
    "ማጠጣት": "irrigation watering schedule",
    "jallisii": "irrigation watering schedule",
    "ድርቅ": "drought tolerance moisture management",
    "hongee": "drought moisture management",
    "አፈር": "soil fertility improvement vertisol drainage",
    "biyyoo": "soil fertility vertisol",
    "ምርት": "crop yield increase production",
    "midhaan": "crop yield harvesting",
    "ማጨድ": "harvesting time maturity post-harvest",
    "haamuu": "harvesting time maturity",
    "ማከማቸት": "post-harvest storage grain protection",
}


def is_agricultural_snippet(title: str, snippet: str) -> bool:
    """Filter out explicit non-agricultural spam (music, entertainment, movies)."""
    text = f"{title} {snippet}".lower()
    for junk in JUNK_KEYWORDS:
        if junk in text:
            return False
    # If the snippet has meaningful content, retain it
    return len(snippet.strip()) >= 25


def build_search_queries(user_text: str, crop: str | None = None, language: str = "am") -> list[str]:
    """Build targeted English and multilingual web search queries."""
    queries = []

    # Strip common conversational fillers
    cleaned = user_text
    for filler in [
        "ስለ", "ንገረኝ", "እባክህ", "እባክዎ", "ምንድን ነው", "እንዴት ነው", "ማብራሪያ", "ምን ላድርግ",
        "ይቻላል", "ወይ", "ናት", "ነው", "ነኝ",
        "maaloo", "natti himi", "akkamitti", "maal", "waa'ee", "jiraa"
    ]:
        cleaned = cleaned.replace(filler, "")
    cleaned = cleaned.strip()

    # Match Ethiopian agronomic terms to English keywords
    matched_terms = []
    user_lower = user_text.lower()
    for term, expansion in ETHIO_AGRI_TERM_MAP.items():
        if term in user_lower:
            matched_terms.append(expansion)

    if matched_terms:
        # Use top identified concepts
        concept_query = " ".join(matched_terms[:3])
        queries.append(f"Ethiopia {concept_query}")
        crop_prefix = f"Ethiopia {crop} " if crop else "Ethiopia "
        queries.append(f"{crop_prefix}{concept_query} agronomy extension")

    # If specific crop extracted, add general advisory query for that crop
    if crop:
        queries.append(f"Ethiopia {crop} farming production best practices guide")

    # If Romanized text or English present
    has_roman = any("a" <= char <= "z" for char in user_lower)
    if has_roman and cleaned:
        queries.append(f"Ethiopia {cleaned} farming agriculture")

    # Fallback broad Ethiopian agricultural query
    queries.append(f"Ethiopia agriculture {cleaned} farming guide")

    # Remove duplicates while preserving order
    unique_queries = []
    for q in queries:
        q_norm = " ".join(q.split())
        if q_norm and q_norm not in unique_queries:
            unique_queries.append(q_norm)

    return unique_queries[:3]


async def search_agricultural_web(
    user_text: str,
    crop: str | None = None,
    language: str = "am",
    max_passages: int = 4
) -> list[dict[str, Any]]:
    """Execute live web search and return vetted agricultural passages for LLM RAG."""
    queries = build_search_queries(user_text, crop=crop, language=language)
    logger.info("Generated web search queries for '%s': %s", user_text, queries)

    all_snippets = []
    seen_texts = set()

    for q in queries:
        try:
            # DuckDuckGo Lite search
            ddg_results = await search_duckduckgo_lite(q, max_results=4)
            for r in ddg_results:
                snip = r["snippet"]
                title = r["title"]
                if snip not in seen_texts and is_agricultural_snippet(title, snip):
                    seen_texts.add(snip)
                    all_snippets.append(r)
                    if len(all_snippets) >= max_passages:
                        break
        except Exception as e:
            logger.warning("DuckDuckGo error on query '%s': %s", q, e)

        if len(all_snippets) >= max_passages:
            break

        try:
            # Wikipedia search fallback
            wiki_results = await search_wikipedia(q, max_results=2)
            for r in wiki_results:
                snip = r["snippet"]
                title = r["title"]
                if snip not in seen_texts and is_agricultural_snippet(title, snip):
                    seen_texts.add(snip)
                    all_snippets.append(r)
                    if len(all_snippets) >= max_passages:
                        break
        except Exception as e:
            logger.warning("Wikipedia error on query '%s': %s", q, e)

        if len(all_snippets) >= max_passages:
            break

    # Format into RAG passage structure
    passages = []
    for idx, item in enumerate(all_snippets[:max_passages]):
        passages.append({
            "chunk_id": f"web_search_{idx+1}",
            "title": item["title"],
            "source_tier": "tier_1",
            "text": item["snippet"],
            "score": round(0.95 - (idx * 0.05), 2),
        })

    logger.info("Retrieved %d live agricultural web passages for query '%s'", len(passages), user_text)
    return passages

