"""Agricultural Knowledge Base Hybrid Retrieval Engine.

Implements:
1. Dense Vector Similarity Search via PostgreSQL pgvector cosine distance.
2. BM25 Lexical Keyword Search for Ethiopian vernacular terms, local weed names, and fertilizers.
3. Reciprocal Rank Fusion (RRF) combining dense semantic and sparse lexical rankings.
4. Local Cross-Reranking with Geographic & Agroecological Boosts:
   - Specific Locality match (town / woreda) -> Top boost (+0.20)
   - Regional state & zone evidence -> Regional boost (+0.12)
   - Agroecological zone matching (Highland/Dega, Midland, Lowland/Kolla) -> Context boost (+0.08)
5. Zero pseudo-randomness, strict adherence to Rule 9.
"""
import logging
import math
import re
from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from app.config import settings
    from app.database.models import AgriculturalDocument, KnowledgeChunk
    from app.rag.embed import get_embedding_provider
except ImportError:
    from backend.app.config import settings
    from backend.app.database.models import AgriculturalDocument, KnowledgeChunk
    from backend.app.rag.embed import get_embedding_provider

logger = logging.getLogger("hello_farmer.rag.retrieve")


class RetrievedPassage(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    source_tier: int
    score: float  # Hybrid RRF score + geographic relevance boost (0.0 to 1.0+)
    dense_score: float = 0.0
    bm25_score: float = 0.0
    crop: str | None = None
    topic: str | None = None
    page_number: int | None = None
    is_placeholder: bool = False
    geographic_tier: str = "national"  # locality, regional, agroecological, national
    locality_match: str | None = None


# Regional keywords mapping for content search
REGION_SYNONYMS = {
    "Oromia": [
        "oromia", "oromiyaa", "ኦሮሚያ", "arsi", "አርሲ", "shewa", "ሸዋ", "bale", "ባሌ",
        "jimma", "ጅማ", "wollega", "ወለጋ", "kulumsa", "ኩሉምሳ", "bako", "ባኮ",
        "melkassa", "መልካሳ", "holeta", "ሆለታ", "adama", "አዳማ", "bishoftu", "ቢሾፍቱ"
    ],
    "Amhara": [
        "amhara", "አማራ", "gojjam", "ጎጃም", "wollo", "ወሎ", "gondar", "ጎንደር",
        "shewa", "ሸዋ", "debre birhan", "ደብረ ብርሃን", "bahir dar", "ባህር ዳር",
        "adet", "አዴት", "sirinka", "ስሪንቃ", "kombolcha", "ኮምቦልቻ"
    ],
    "Tigray": ["tigray", "ትግራይ", "mekelle", "መቀሌ", "መቐለ", "shire", "ሽሬ", "alamata", "አላማጣ", "axum", "አክሱም"],
    "Sidama": ["sidama", "ሲዳማ", "hawassa", "ሀዋሳ", "awassa", "አዋሳ", "wondo genet", "ወንዶ ገነት"],
    "South Ethiopia": ["wolaita", "ዎላይታ", "sodo", "ሶዶ", "arba minch", "አርባ ምንጭ", "gamo", "ጋሞ", "gedeo", "ጌዴኦ"],
    "Central Ethiopia": ["gurage", "ጉራጌ", "butajira", "ቡታጅራ", "hadiya", "ሃዲያ", "hossana", "ሆሳዕና"],
    "Somali": ["somali", "ሶማሌ", "jigjiga", "ጅግጅጋ", "gode", "ጎዴ"],
    "Afar": ["afar", "አፋር", "semera", "ሰመራ", "awash", "አዋሽ"],
    "Benishangul-Gumuz": ["benishangul", "ቤንሻንጉል", "assosa", "አሶሳ", "bambasi", "ባምባሲ"],
    "Gambella": ["gambella", "ጋምቤላ", "itang", "ኢታንግ", "abobo", "አቦቦ"],
}

AGROECOLOGY_KEYWORDS = {
    "Highland": [
        "highland", "dega", "ደጋ", "frost", "ውርጭ", "vertisol", "black soil",
        "አሲዳማ", "acidic", "nitisol", "cool", "cold", "ቀዝቃዛ", "2400m", "2500m", "2600m", "2800m"
    ],
    "Midland": [
        "midland", "weyna dega", "ወይና ደጋ", "medium rainfall", "loam", "1800m", "2000m", "2200m"
    ],
    "Lowland": [
        "lowland", "kolla", "ቆላ", "bereha", "በረሃ", "drought", "ድርቅ",
        "semi-arid", "arid", "warm", "hot", "ሞቃት", "1500m", "1200m", "1000m"
    ],
}


def tokenize_ethiopian_text(text: str) -> list[str]:
    """Tokenize multilingual Ethiopian text into words and sub-tokens.
    
    Preserves Ge'ez fidel script characters (\u1200-\u137F) and Latin alphabets.
    """
    if not text:
        return []
    tokens = re.findall(r"[\w\u1200-\u137F]+", text.lower())
    return [t for t in tokens if len(t) > 1]


def compute_bm25_scores(
    query_tokens: list[str],
    documents: list[list[str]],
    k1: float = 1.2,
    b: float = 0.75,
) -> list[float]:
    """Compute BM25 scores for a list of tokenized documents given query tokens."""
    n_docs = len(documents)
    if n_docs == 0 or not query_tokens:
        return [0.0] * n_docs

    doc_lengths = [len(doc) for doc in documents]
    avg_len = sum(doc_lengths) / max(n_docs, 1)

    # Document frequency
    df: dict[str, int] = {}
    for doc in documents:
        seen = set(doc)
        for t in seen:
            df[t] = df.get(t, 0) + 1

    scores = []
    for i, doc in enumerate(documents):
        doc_len = doc_lengths[i]
        score = 0.0
        doc_freqs: dict[str, int] = {}
        for t in doc:
            doc_freqs[t] = doc_freqs.get(t, 0) + 1

        for q in query_tokens:
            if q not in df:
                continue
            # Smoothed Robertson-Spärck Jones IDF
            q_df = df[q]
            idf = math.log((n_docs - q_df + 0.5) / (q_df + 0.5) + 1.0)
            tf = doc_freqs.get(q, 0)
            num = tf * (k1 + 1.0)
            den = tf + k1 * (1.0 - b + b * (doc_len / max(avg_len, 1.0)))
            score += idf * (num / max(den, 1e-6))
        scores.append(score)

    return scores


def reciprocal_rank_fusion(
    dense_ranks: dict[str, int],
    bm25_ranks: dict[str, int],
    k: int = 60,
    dense_weight: float = 1.0,
    bm25_weight: float = 0.8,
) -> dict[str, float]:
    """Compute Reciprocal Rank Fusion (RRF) scores across dense and sparse rankings."""
    all_ids = set(dense_ranks.keys()) | set(bm25_ranks.keys())
    rrf_scores: dict[str, float] = {}
    for doc_id in all_ids:
        score = 0.0
        if doc_id in dense_ranks:
            score += dense_weight / (k + dense_ranks[doc_id])
        if doc_id in bm25_ranks:
            score += bm25_weight / (k + bm25_ranks[doc_id])
        rrf_scores[doc_id] = score
    return rrf_scores


async def retrieve_passages(
    query: str,
    session: AsyncSession,
    top_k: int = 4,
    similarity_threshold: float | None = None,
    crop_filter: str | None = None,
    location: Any | None = None,
    region_filter: str | None = None,
) -> list[RetrievedPassage]:
    """Retrieve top-k relevant knowledge passages using Hybrid RAG (pgvector + BM25 + RRF)."""
    if not query or not query.strip():
        return []

    threshold = similarity_threshold if similarity_threshold is not None else getattr(
        settings, "SIMILARITY_THRESHOLD", 0.65
    )

    embedder = get_embedding_provider()
    query_vector = await embedder.embed_query(query)
    query_tokens = tokenize_ethiopian_text(query)

    # 1. Candidate pool retrieval via pgvector
    cosine_dist = KnowledgeChunk.embedding.cosine_distance(query_vector)

    stmt = (
        select(
            KnowledgeChunk,
            AgriculturalDocument.title.label("doc_title"),
            AgriculturalDocument.source_tier.label("doc_tier"),
            (1.0 - cosine_dist).label("dense_similarity"),
        )
        .join(AgriculturalDocument, KnowledgeChunk.document_id == AgriculturalDocument.id)
        .where(KnowledgeChunk.embedding.is_not(None))
    )

    if crop_filter:
        stmt = stmt.where(KnowledgeChunk.crop == crop_filter)

    # Retrieve candidate pool for hybrid rank fusion (30 candidates)
    stmt = stmt.order_by(cosine_dist.asc()).limit(max(top_k * 6, 30))

    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    # 2. Compute Dense Ranks
    dense_ranks: dict[str, int] = {}
    dense_scores_map: dict[str, float] = {}
    row_map: dict[str, tuple] = {}
    doc_tokens_list: list[list[str]] = []
    chunk_ids_order: list[str] = []

    for rank, (chunk, doc_title, doc_tier, dense_sim) in enumerate(rows, start=1):
        c_id = chunk.id
        dense_ranks[c_id] = rank
        dense_scores_map[c_id] = float(dense_sim) if dense_sim is not None else 0.0
        row_map[c_id] = (chunk, doc_title, doc_tier)
        doc_tokens_list.append(tokenize_ethiopian_text(chunk.content or ""))
        chunk_ids_order.append(c_id)

    # 3. Compute BM25 Lexical Scores and Ranks
    raw_bm25 = compute_bm25_scores(query_tokens, doc_tokens_list)
    bm25_with_ids = list(zip(chunk_ids_order, raw_bm25))
    # Sort descending by BM25 score
    bm25_with_ids.sort(key=lambda x: x[1], reverse=True)
    bm25_ranks: dict[str, int] = {c_id: r for r, (c_id, _) in enumerate(bm25_with_ids, start=1)}
    bm25_scores_map: dict[str, float] = {c_id: score for c_id, score in bm25_with_ids}

    # 4. Reciprocal Rank Fusion
    rrf_map = reciprocal_rank_fusion(dense_ranks, bm25_ranks, k=60, dense_weight=1.0, bm25_weight=0.8)

    # Extract target geographic tokens
    target_town = ""
    target_town_am = ""
    target_town_om = ""
    target_woreda = ""
    target_zone = ""
    target_region = region_filter or ""
    target_agroecology = ""

    if location:
        target_town = (getattr(location, "town", "") or getattr(location, "name", "")).lower()
        target_town_am = getattr(location, "name_am", "")
        target_town_om = getattr(location, "name_om", "").lower()
        target_woreda = (getattr(location, "woreda", "") or "").lower()
        target_zone = (getattr(location, "zone", "") or "").lower()
        target_region = getattr(location, "region", "") or target_region
        target_agroecology = getattr(location, "agroecological_zone", "")

    regional_synonyms = REGION_SYNONYMS.get(target_region, [])
    agro_keywords = AGROECOLOGY_KEYWORDS.get(target_agroecology, [])

    # 5. Local Cross-Reranker and Geographic Context Boosting
    candidate_passages: list[RetrievedPassage] = []

    # Normalize RRF to 0.0 - 1.0 range
    max_rrf = max(rrf_map.values()) if rrf_map else 1.0
    min_rrf = min(rrf_map.values()) if rrf_map else 0.0
    rrf_span = max(max_rrf - min_rrf, 1e-6)

    for c_id, (chunk, doc_title, doc_tier) in row_map.items():
        base_rrf = (rrf_map.get(c_id, 0.0) - min_rrf) / rrf_span
        dense_score = dense_scores_map.get(c_id, 0.0)
        bm25_score = bm25_scores_map.get(c_id, 0.0)

        # Baseline blended score
        fused_score = 0.55 * dense_score + 0.45 * base_rrf

        content_lower = (chunk.content or "").lower()
        doc_lower = (doc_title or "").lower()

        geo_tier = "national"
        locality_match_name = None
        geo_boost = 0.0

        # Tier 1 Geographic Priority: Specific Locality Match (Town / Woreda)
        if target_town and (
            target_town in content_lower
            or (target_town_am and target_town_am in (chunk.content or ""))
            or (target_town_om and target_town_om in content_lower)
            or (target_woreda and target_woreda in content_lower)
            or target_town in doc_lower
        ):
            geo_tier = "locality"
            locality_match_name = getattr(location, "name", target_town)
            geo_boost = 0.20

        # Tier 2 Geographic Priority: Regional State / Zone
        elif target_region and (
            target_region.lower() in content_lower
            or any(syn in content_lower for syn in regional_synonyms)
            or (target_zone and target_zone in content_lower)
            or target_region.lower() in doc_lower
        ):
            geo_tier = "regional"
            locality_match_name = target_region
            geo_boost = 0.12

        # Tier 3 Geographic Priority: Agroecological Zone
        elif target_agroecology and any(kw in content_lower for kw in agro_keywords):
            geo_tier = "agroecological"
            locality_match_name = f"{target_agroecology} agroecological zone"
            geo_boost = 0.08

        final_score = fused_score + geo_boost

        if final_score < threshold:
            continue

        is_ph = (doc_tier == 0 or "placeholder" in (doc_title or "").lower())
        candidate_passages.append(
            RetrievedPassage(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=doc_title or "Agricultural Guide",
                content=chunk.content,
                source_tier=doc_tier,
                score=round(final_score, 4),
                dense_score=round(dense_score, 4),
                bm25_score=round(bm25_score, 4),
                crop=chunk.crop,
                topic=chunk.topic,
                page_number=chunk.page_number,
                is_placeholder=is_ph,
                geographic_tier=geo_tier,
                locality_match=locality_match_name,
            )
        )

    # Final Sort by hybrid fused score
    candidate_passages.sort(key=lambda p: p.score, reverse=True)
    return candidate_passages[:top_k]
