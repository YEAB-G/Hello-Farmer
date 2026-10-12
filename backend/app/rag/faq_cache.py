"""Semantic FAQ Cache for high-frequency Ethiopian agricultural questions.

Provides instant (<50ms) verified agronomic responses for common seasonal outbreaks
and fertilizer inquiries without making external LLM or search calls.
"""
from dataclasses import dataclass
import re
from typing import Optional


@dataclass
class FAQMatch:
    answer: str
    english_gloss: str
    topic: str
    source_title: str
    confidence: float = 0.98


# Pre-vetted high-frequency Ethiopian agricultural Q&As
VETTED_FAQS_AM = [
    {
        "keywords": ["ጤፍ", "ማዳበሪያ", "ዩሪያ", "ኤን ፒ ኤስ", "መጠን"],
        "answer": "ለጤፍ ሰብል በመዝሪያ ወቅት መቶ ኪሎ ግራም ኤን ፒ ኤስ ይጨመራል። ከዘሩ ከሰላሳ ቀናት በኋላ አረም ከተነቀለ በኋላ ሃምሳ ኪሎ ግራም ዩሪያ ይረጩ። የአፈርዎን አይነት ከልማት ጣቢያ ባለሙያ ጋር ያረጋግጡ።",
        "gloss": "For teff, apply one hundred kg NPS at planting, followed by fifty kg Urea topdressing thirty days after sowing after weeding. Confirm with your local DA.",
        "topic": "fertilizer",
        "source": "MoA / EIAR National Teff Production Manual",
    },
    {
        "keywords": ["ስንዴ", "ዝገት", "ዋግ", "ቢጫ"],
        "answer": "የስንዴ ቢጫ ዝገት በሽታን ለመከላከል ሰብሉ አየር እንዲያገኝ ያድርጉ፤ እርጥበት እንዳይበዛ ተጠንቀቁ። በሽታው ከታየ በሄክታር ግማሽ ሊትር ፀረ-ፈንገስ መድኃኒት በማለዳ ይርጩ። ዝርዝር መድኃኒቱን ከልማት ጣቢያ ባለሙያ ጋር ያረጋግጡ።",
        "gloss": "To prevent wheat yellow rust, ensure field aeration and avoid excess moisture. Spray half a liter of fungicide per hectare in the early morning; confirm with your DA.",
        "topic": "crop_disease",
        "source": "EIAR Wheat Rust Management Advisory",
    },
    {
        "keywords": ["በቆሎ", "ተምች", "ኩብኩባ"],
        "answer": "የበቆሎ ተምች ወይም ኩብኩባን ለመከላከል በማለዳ የበቆሎውን እምብርት በእጅ ወይም አመድ በመጨመር ይከላከሉ። ተባዩ ከበረታ በሄክታር ሁለት መቶ ሚሊ ሊትር ፀረ-ተባይ መድኃኒት ይርጩ። መርጨት ያለባችሁን ወቅት ከልማት ጣቢያ ባለሙያ ይጠይቁ።",
        "gloss": "For fall armyworm on maize, check leaf funnels in the morning and apply wood ash or handpick. For severe infestations, spray two hundred ml insecticide per hectare; consult your DA.",
        "topic": "pest_control",
        "source": "MoA Fall Armyworm Emergency Action Guide",
    },
    {
        "keywords": ["በቆሎ", "ቅጠል", "ሰደድ", "ማቃጠል"],
        "answer": "የበቆሎ ቅጠል ሰደድ በሽታ እርጥበት ሲበዛ የሚከሰት ፈንገስ ነው። የተጠቁትን የታችኛውን ቅጠሎች በማስወገድ አየር እንዲያገኝ ያድርጉ። አስፈላጊ ከሆነ የተፈቀደ ፀረ-ፈንገስ መድኃኒት ከልማት ጣቢያ ባለሙያ ጋር ያማክሩ።",
        "gloss": "Maize leaf blight is caused by fungal humidity. Remove lower infected leaves to improve air circulation, and consult your DA for approved fungicide.",
        "topic": "crop_disease",
        "source": "Bako Agricultural Research Center Guide",
    },
    {
        "keywords": ["ቡና", "ፍሬ", "በሽታ", "ማድረቅ"],
        "answer": "የቡና ፍሬ በሽታን ለመከላከል የቡናውን ዛፍ ቅርንጫፍ በመግረዝ ፀሐይና አየር እንዲያገኝ ያድርጉ። የረገፉ የበሰበሱ ፍሬዎችን ሰብስባችሁ አቃጥሉ። የፀረ-ፈንገስ ርጭት ጊዜን ከልማት ጣቢያ ባለሙያ ጋር ያረጋግጡ።",
        "gloss": "For coffee berry disease, prune shade branches to improve sunlight and air flow, burn dropped infected berries, and confirm spray schedule with your DA.",
        "topic": "crop_disease",
        "source": "Jimma Agricultural Research Center Coffee Advisory",
    },
    {
        "keywords": ["አፈር", "አሲድ", "ኖራ"],
        "answer": "የአፈር አሲዳማነትን ለማከም በእርሻ ወቅት የግብርና ኖራ በሄክታር ከሁለት እስከ ሶስት ቶን መጨመር ይመረጣል። ኖራውን ከዘር በፊት ከሁለት ሳምንት በፊት ከአፈሩ ጋር በደንብ ይደባልቁ። የአፈርዎን ናሙና በልማት ጣቢያ ባለሙያ ያስመርምሩ።",
        "gloss": "To treat soil acidity, apply two to three tons of agricultural lime per hectare two weeks before sowing, mixing thoroughly with soil. Test your soil with your DA.",
        "topic": "soil_management",
        "source": "Ethiopian Soil Health & Lime Guidelines",
    },
]

VETTED_FAQS_OM = [
    {
        "keywords": ["xaafii", "xaa'oo", "yuuriyaa", "nps"],
        "answer": "Midhaan xaafiif yeroo facaasaatti hektaara tokkoof NPS kiiloo dhibba tokko fayyadamaa. Facaasaa irraa guyyaa soddoma booda aramaa qulqulleessitanii yuuriyaa kiiloo shantama facaasaa. Ogeessa misooma qonnaa mariisisaa.",
        "gloss": "For teff, apply 100 kg NPS at planting, and 50 kg Urea topdressing 30 days later after weeding. Consult your local DA.",
        "topic": "fertilizer",
        "source": "Oromia Bureau of Agriculture Teff Manual",
    },
    {
        "keywords": ["qamadii", "waagii", "keelloo"],
        "answer": "Dhukkuba waagii qamadii ittisuuf ooyiruun qilleensa akka argatu godhaa. Dhukkubni yoo mul'ate ganama barii hektaara tokkoof farra fangasii liitira walakkaa biiffaa. Qoricha sirrii ogeessa misooma qonnaa irraa mirkaneeffadhaa.",
        "gloss": "For wheat yellow rust, maintain aeration. Spray half a liter of fungicide per hectare early in the morning; verify with your DA.",
        "topic": "crop_disease",
        "source": "EIAR Wheat Rust Advisory",
    },
    {
        "keywords": ["boqqoolloo", "kormaa", "ilbiisa"],
        "answer": "Kormaa boqqoolloo ittisuuf ganama baala keessa ilaalaa yookiin daaraa naqaa. Yoo heddummaate farra ilbiisaa hektaara tokkoof miilii liitira dhibba lama biiffaa. Yeroo biifaa ogeessa qonnaa gaafadhaa.",
        "gloss": "For fall armyworm on maize, inspect whorls in the morning or apply wood ash. For high infestation, spray 200 ml insecticide per hectare; check with your DA.",
        "topic": "pest_control",
        "source": "MoA Pest Management Advisory",
    },
]


def match_agricultural_faq(query: str, language: str = "am") -> Optional[FAQMatch]:
    """Match user query against high-frequency vetted agronomic solutions.

    Returns FAQMatch if confidence exceeds threshold, else None.
    """
    if not query or len(query.strip()) < 4:
        return None

    q_lower = query.lower().strip()
    faqs = VETTED_FAQS_OM if language == "om" else VETTED_FAQS_AM

    best_match = None
    max_score = 0.0

    for item in faqs:
        matched_keywords = sum(1 for kw in item["keywords"] if kw.lower() in q_lower)
        if len(item["keywords"]) == 0:
            continue
        score = matched_keywords / len(item["keywords"])

        # Require at least 2 distinct keywords matched and score >= 0.50
        if matched_keywords >= 2 and score >= 0.50:
            if score > max_score:
                max_score = score
                best_match = item

    if best_match and max_score >= 0.50:
        return FAQMatch(
            answer=best_match["answer"],
            english_gloss=best_match["gloss"],
            topic=best_match["topic"],
            source_title=best_match["source"],
            confidence=0.98,
        )

    return None
