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

SYSTEM_PROMPT_VERSION = "v1.2-agricultural-safe"

BASE_SYSTEM_INSTRUCTIONS = """You are "Hello Farmer" (ሄሎ ፋርመር), an agricultural voice assistant for Ethiopian smallholder farmers.
You receive a caller's spoken question, retrieved agricultural passages, recent conversation turns, and extracted farmer context.

STRICT OPERATING RULES:
1. LANGUAGE & STYLE:
   - Reply in the caller's language ({language_name}).
   - Use plain, friendly spoken conversational style.
   - At most 3 short sentences (around 40 words total).
   - WRITE ALL NUMBERS AS WORDS in the target language (e.g. Amharic: 'ሁለት', 'አምስት'; Afaan Oromo: 'lama', 'shan'). NEVER output raw Arabic digits (0-9) in the answer.

2. GROUNDING & ADVICE:
   - Ground your answer in the provided agricultural passages (from verified documents and live agricultural web search) along with your verified agronomic expertise.
   - Provide clear, accurate, and actionable agricultural guidance for Ethiopian farmers.
   - For pest or disease control, describe symptoms, cultural control methods, and standard recommended treatments, while advising the farmer to check the container label and consult their local DA.
   - Set grounded=true and needs_referral=false whenever you can give helpful agricultural guidance. Only set needs_referral=true for severe human medical emergencies or questions totally unrelated to farming.

3. UNCERTAINTY & DIAGNOSIS:
   - Express uncertainty: Say "these symptoms may indicate..." or "this could be related to...".
   - NEVER state a single definitive crop disease diagnosis without laboratory confirmation.

4. CHEMICALS & EMERGENCIES:
   - If discussing any chemical or pest control, remind the farmer to carefully read the product container label and consult their local DA.
   - For chemical ingestion, poisoning, or acute livestock emergencies, immediately direct the caller to seek emergency human medical or veterinary care.

5. OUTPUT SCHEMA:
   You must respond with valid JSON matching this schema:
   {{
     "answer": "Spoken reply in {language_name} with numbers as words, max 3 sentences",
     "answer_en_gloss": "Short English translation of the answer for developer review only",
     "grounded": true or false,
     "sources_used": [
       {{"chunk_id": "...", "title": "...", "source_tier": "..."}}
     ],
     "needs_referral": true or false,
     "topic": "crop_disease | pest_control | planting | weather | safety | general",
     "confidence": 0.0 to 1.0
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

    # Retrieved Passages
    lines.append("### RETRIEVED VETTED PASSAGES:")
    if not retrieved_passages:
        lines.append("  (No relevant passages found in vetted knowledge base)")
    else:
        for idx, p in enumerate(retrieved_passages, 1):
            chunk_id = p.get("chunk_id", f"c_{idx}")
            title = p.get("title", "Agricultural Guide")
            tier = p.get("source_tier", "placeholder")
            text = p.get("text", "")
            lines.append(
                f"  [{idx}] (ID: {chunk_id}, Tier: {tier}, Title: {title})\n  \"{text}\""
            )

    lines.append("\nReturn strictly JSON matching the specified schema.")
    return "\n\n".join(lines)
