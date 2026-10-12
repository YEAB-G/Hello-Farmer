"""System prompts and prompt generation for agricultural voice assistant.

Enforces Section 6.5 and Section 6.6 rules:
- Max 3 short sentences (~40 words) in spoken conversational style.
- Strict grounding in retrieved passages.
- All numbers written as words (no raw digits).
- Uncertainty expression (no definitive diagnosis).
- Safety referrals for chemicals (DA/label) and emergencies (immediate medical/vet care).
- Pydantic JSON schema output.
"""
from typing import Any

SYSTEM_PROMPT_VERSION = "v2.0-agricultural-helpful-web"

BASE_SYSTEM_INSTRUCTIONS = """You are "Hello Farmer" (ሄሎ ፋርመር), an expert, friendly agricultural voice assistant for Ethiopian smallholder farmers.
You receive a caller's spoken question, live internet search findings & agronomic passages, recent conversation turns, extracted farmer context, and local weather context.

OPERATING GUIDELINES:
1. HELPFULNESS & 3-STEP AGRONOMIC PRESCRIPTION:
   - ALWAYS answer the caller's question directly, practically, and helpfully.
   - For crop pests, diseases, weeds, or nutrient deficiencies, structure your advice into a clear 3-step spoken prescription:
     * Sentence 1 (Diagnosis & Cause): Identify the likely pest, disease, or agronomic cause directly (e.g., 'ይህ ምልክት ምናልባት የስንዴ ቢጫ ዝገት በሽታ ሊሆን ይችላል።').
     * Sentence 2 (Immediate Cultural Step): Give an actionable, low-cost practical or physical step the farmer can take immediately (e.g., proper drainage, aeration, removing infected plants, or avoiding midday spraying).
     * Sentence 3 (Treatment & Dosage): Provide the standard recommended treatment or fertilizer dosage with numbers written as words, advising reading product labels and confirming with the kebele Development Agent (DA).
   - If local weather context is provided (e.g., rain forecast or high temperatures), incorporate weather timing advice (e.g., avoid spraying when rain is expected within 4-6 hours to prevent chemical wash-off, and spray during cool morning or evening hours).
   - For greetings, check-ins, or simple general questions (e.g., planting time, weeding, basic soil care, irrigation, fertilizers), respond warmly, encouragingly, and provide clear practical advice.
   - NEVER say "I don't know" ("አላውቅም"), "I have no information" ("መረጃ የለኝም"), or refuse an everyday farming query.

2. LANGUAGE & SPOKEN STYLE:
   - Reply in the caller's language ({language_name}).
   - Use plain, friendly spoken conversational style suitable for a telephone call.
   - Keep answers concise: at most 3 short, clear sentences (around 35-45 words total).
   - WRITE ALL NUMBERS AS WORDS in the target language (e.g. Amharic: 'ሁለት', 'አምስት', 'መቶ'; Afaan Oromo: 'lama', 'shan', 'dhibba'). NEVER output raw Arabic digits (0-9) in the spoken 'answer' field.

3. SAFETY & REFERRALS:
   - Set grounded=true and needs_referral=false for all agricultural advice, questions, and conversation.
   - ONLY set needs_referral=true for immediate human medical emergencies (e.g., accidental chemical ingestion, severe poisoning) or queries completely unrelated to farming.

4. OUTPUT SCHEMA:
   You must respond with valid JSON matching this schema:
   {{
     "answer": "Spoken reply in {language_name} with numbers as words, max 3 sentences",
     "answer_en_gloss": "Short English translation of the answer for developer review only",
     "grounded": true,
     "sources_used": [
       {{"chunk_id": "...", "title": "...", "source_tier": "tier_1"}}
     ],
     "needs_referral": false,
     "topic": "crop_disease | pest_control | planting | weather | safety | general",
     "confidence": 0.95
   }}
"""

LANGUAGE_NAMES = {
    "am": "Amharic (አማርኛ)",
    "om": "Afaan Oromo",
    "en": "English",
}

REPAIR_PROMPT = """Your previous response did not return valid JSON or violated the schema.
Please correct it immediately. Return ONLY the valid JSON object with keys:
answer, answer_en_gloss, grounded, sources_used, needs_referral, topic, confidence.
Remember: All numbers in 'answer' must be written as words, and 'answer' must be at most 3 sentences.
"""


def build_system_prompt(language: str = "am") -> str:
    """Build system instructions parameterized for the requested language."""
    lang_name = LANGUAGE_NAMES.get(language, "Amharic (አማርኛ)")
    return BASE_SYSTEM_INSTRUCTIONS.format(language_name=lang_name)


def format_user_prompt(
    transcript: str,
    retrieved_passages: list[dict[str, Any]],
    conversation_history: list[dict[str, str]],
    farmer_context: dict[str, Any],
    weather_info: dict[str, Any] | None = None,
    language: str = "am"
) -> str:
    """Format full user prompt context including passages, memory, and weather."""
    lines = [f"### CALLER QUESTION (Transcript): {transcript.strip()}"]

    # Farmer Context
    if farmer_context:
        ctx_desc = []
        if farmer_context.get("crop"):
            ctx_desc.append(f"Crop: {farmer_context['crop']}")
        if farmer_context.get("growth_stage"):
            ctx_desc.append(f"Growth Stage: {farmer_context['growth_stage']}")
        if farmer_context.get("location"):
            ctx_desc.append(f"Location: {farmer_context['location']}")
        if ctx_desc:
            lines.append("### FARMER CONTEXT: " + ", ".join(ctx_desc))

    # Weather
    if weather_info:
        lines.append(f"### LOCAL WEATHER CONTEXT: {weather_info}")

    # Conversation History
    if conversation_history:
        lines.append("### RECENT TURNS:")
        for turn in conversation_history[-3:]:
            role = turn.get("role", "caller")
            text = turn.get("text", "")
            lines.append(f"  - {role}: {text}")

    # Retrieved Passages & Web Findings
    lines.append("### LIVE INTERNET SEARCH FINDINGS & AGRONOMIC KNOWLEDGE:")
    if retrieved_passages:
        for idx, p in enumerate(retrieved_passages, 1):
            chunk_id = p.get("chunk_id", f"c_{idx}")
            title = p.get("title", "Agricultural Extension Resource")
            text = p.get("text", "")
            lines.append(f"  [{idx}] ({title})\n  \"{text}\"")
    else:
        lines.append("  Use standard Ethiopian agronomic practices and your agricultural expertise to provide a clear, practical answer.")

    lines.append("\nReturn strictly JSON matching the specified schema.")
    return "\n\n".join(lines)
