"""Post-call advice summarizer for SMS dispatch.

Generates concise agricultural recommendations (advice only, no conversational transcripts)
formatted for SMS segment constraints in the caller's language.
"""
import re


def generate_post_call_sms_summary(
    last_advice: str | None,
    reached_answer: bool,
    language: str = "am",
    crop: str | None = None,
) -> str:
    """Generate concise post-call agronomic advice text for SMS dispatch."""
    if language == "om":
        prefix = "Heelo Faarmar: "
        if not reached_answer or not last_advice:
            return (
                f"{prefix}Gorsa dabalataaf ogeessa qonnaa naannoo keessanii "
                f"mariisisaa yookiin sarara 8028 bilbilaa."
            )
        # Strip conversational greetings
        clean = re.sub(
            r"^(Baga gara Heelo Faarmar nagaan dhuftan|Akkam|Nagaa)\.?\s*",
            "",
            last_advice.strip(),
            flags=re.IGNORECASE,
        )
        return f"{prefix}{clean}"

    else:  # Amharic default
        prefix = "ሄሎ ፋርመር፡ "
        if not reached_answer or not last_advice:
            return (
                f"{prefix}ለተጨማሪ የግብርና ማብራሪያ የአካባቢዎን የልማት ጣቢያ ባለሙያ (DA) "
                f"ያማክሩ ወይም ወደ 8028 ይደውሉ።"
            )
        # Strip conversational greetings
        clean = re.sub(
            r"^(እንኳን ወደ ሄሎ ፋርመር በደህና መጡ|ጤና ይስጥልኝ|ሰላም)\.?\s*",
            "",
            last_advice.strip(),
        )
        return f"{prefix}{clean}"
