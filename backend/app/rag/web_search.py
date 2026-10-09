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
    "ማዳበሪያ", "ሰብል", "እርሻ", "በሽታ", "ተባይ", "ምርት", "ጤፍ", "ስንዴ", "በቆሎ", "አፈር", "ኬሚካል", "ዝናብ",
    "qamadii", "xaafii", "boqqoolloo", "xaa'oo", "hoomaa", "rooba"
}

JUNK_KEYWORDS = {
    "youtube", "ቀሚስ", "ሙዚቃ", "ፊልም", "ዜና", "ቪዲዮ", "አየር መንገድ", "ሰበር", "መዝሙር",
    "ቤተክርስቲያን", "song", "video", "airline", "dress", "fashion", "wedding", "qophii"
}


def is_agricultural_snippet(title: str, snippet: str) -> bool:
    """Filter out non-agricultural web search results (music, clothes, news, politics)."""
    text = f"{title} {snippet}".lower()
    for junk in JUNK_KEYWORDS:
        if junk in text:
            return False
    return any(kw in text for kw in AGRICULTURAL_KEYWORDS)


def build_search_queries(user_text: str, crop: str | None = None, language: str = "am") -> list[str]:
    """Build targeted English and multilingual web search queries."""
    queries = []

    # Strip common filler phrases in Amharic and Afaan Oromo
    cleaned = user_text
    for filler in [
        "ስለ", "ንገረኝ", "እባክህ", "እባክዎ", "ምንድን ነው", "እንዴት ነው", "ማብራሪያ", "ምን ላድርግ",
        "maaloo", "natti himi", "akkamitti", "maal", "waa'ee"
    ]:
        cleaned = cleaned.replace(filler, "")
    cleaned = cleaned.strip()

    # If query is in Amharic script (Ethiopic Unicode \u1200-\u137F), add keyword expansions FIRST
    has_ethiopic = any("\u1200" <= char <= "\u137F" for char in user_text)
    if has_ethiopic:
        if "ተምች" in user_text or "ትል" in user_text or "በቆሎ" in user_text:
            queries.append("Ethiopia fall armyworm maize pest control advisory")
        if "ዋግ" in user_text or "ስንዴ" in user_text:
            queries.append("Ethiopia wheat rust disease symptoms management fungicide")
        if "ማዳበሪያ" in user_text or "ዩሪያ" in user_text or "ዳፕ" in user_text or "ኤንፒኤስ" in user_text:
            queries.append("Ethiopia fertilizer recommendation NPS Urea rate teff wheat maize")
        if "ጤፍ" in user_text:
            queries.append("Ethiopia teff row planting seed rate agronomy")
        if "አፈር" in user_text or "ኮምፖስት" in user_text:
            queries.append("Ethiopia integrated soil fertility management ISFM compost")
    else:
        user_lower = user_text.lower()
        if "qamadii" in user_lower or "waagii" in user_lower:
            queries.append("Ethiopia wheat rust management fungicide")
        if "xaa'oo" in user_lower or "yuriyaa" in user_lower:
            queries.append("Ethiopia fertilizer recommendation NPS Urea rate")
        if "boqqoolloo" in user_lower or "hoomaa" in user_lower:
            queries.append("Ethiopia fall armyworm maize pest control")

    # Add general fallback query
    crop_term = f" {crop}" if crop else ""
    queries.append(f"Ethiopia agriculture{crop_term} {cleaned} farming")

    return queries


async def search_agricultural_web(
    user_text: str,
    crop: str | None = None,
    language: str = "am",
    max_passages: int = 4
) -> list[dict[str, Any]]:
    """Execute live web search and return vetted agricultural passages for LLM RAG."""
    queries = build_search_queries(user_text, crop=crop, language=language)
    logger.info("Generated web search queries: %s", queries)

    all_snippets = []
    seen_texts = set()

    for q in queries[:2]:
        # Try DuckDuckGo Lite
        ddg_results = await search_duckduckgo_lite(q, max_results=4)
        for r in ddg_results:
            snip = r["snippet"]
            title = r["title"]
            if snip not in seen_texts and len(snip) > 20 and is_agricultural_snippet(title, snip):
                seen_texts.add(snip)
                all_snippets.append(r)
                if len(all_snippets) >= max_passages:
                    break

        if len(all_snippets) >= max_passages:
            break

        # Also check Wikipedia for agricultural terms
        wiki_results = await search_wikipedia(q, max_results=2)
        for r in wiki_results:
            snip = r["snippet"]
            title = r["title"]
            if snip not in seen_texts and len(snip) > 20 and is_agricultural_snippet(title, snip):
                seen_texts.add(snip)
                all_snippets.append(r)
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
            "score": 0.90 - (idx * 0.05),
        })

    logger.info("Retrieved %d live agricultural web passages for query '%s'", len(passages), user_text)
    return passages

