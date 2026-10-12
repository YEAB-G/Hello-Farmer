"""
Executive Pitch Deck Generator for Hello Farmer (ሄሎ ፋርመር).
Creates:
1. Hello_Farmer_Pitch_Deck.pptx (12 Main Slides + 10 Appendix Slides with Speaker Notes)
2. Hello_Farmer_Pitch_Deck.pdf (Landscape 16:9 executive presentation PDF)
"""

import os
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors as r_colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def build_pitch_deck(pptx_path="Hello_Farmer_Pitch_Deck.pptx", pdf_path="Hello_Farmer_Pitch_Deck.pdf"):
    prs = Presentation()
    # 16:9 Widescreen: 13.333 x 7.5 inches
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Logo paths
    logo_trans_path = Path("frontend/public/hello_farmer_logo_transparent.png")
    logo_jpg_path = Path("frontend/public/hello_farmer_logo.jpg")
    active_logo = str(logo_trans_path if logo_trans_path.exists() else logo_jpg_path)

    # Color Palette Tokens (extracted directly from Hello Farmer official branding)
    C_FOREST = RGBColor(23, 75, 53)          # #174B35 Primary Brand Green
    C_DEEP_GREEN = RGBColor(16, 55, 41)      # #103729 Dark Emerald
    C_LEAF = RGBColor(77, 138, 88)           # #4D8A58 Vibrant Leaf Green
    C_CREAM = RGBColor(247, 245, 236)        # #F7F5EC Warm Editorial Cream
    C_GOLD = RGBColor(217, 164, 65)          # #D9A441 Ethiopian Sun Gold
    C_WHITE = RGBColor(255, 255, 255)        # Pure White
    C_SLATE_DARK = RGBColor(32, 41, 35)      # #202923 Primary Text
    C_SLATE_MUTED = RGBColor(102, 115, 107)  # #66736B Secondary Text
    C_CARD_BORDER = RGBColor(226, 232, 228)  # Subtle border
    C_CARD_BG = RGBColor(255, 255, 255)
    C_LIGHT_BG = RGBColor(249, 250, 249)

    def set_slide_background(slide, color):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, category_text="HELLO FARMER • ሄሎ ፋርመር", is_dark=False):
        # Category Tracker
        cat_box = slide.shapes.add_textbox(Inches(0.9), Inches(0.45), Inches(9.5), Inches(0.35))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(9.5)
        p_cat.font.bold = True
        p_cat.font.color.rgb = C_GOLD if is_dark else C_LEAF

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.9), Inches(0.78), Inches(10.5), Inches(0.8))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.size = Pt(25)
        p_title.font.bold = True
        p_title.font.color.rgb = C_WHITE if is_dark else C_DEEP_GREEN

        # Subtle Header Logo in top right
        if active_logo and os.path.exists(active_logo):
            try:
                slide.shapes.add_picture(active_logo, Inches(12.0), Inches(0.42), Inches(0.55), Inches(0.55))
            except Exception:
                pass

    def add_speaker_note(slide, note_text):
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = note_text

    def add_card(slide, left, top, width, height, title, items, badge="", bg_color=C_CARD_BG, border_color=C_CARD_BORDER, title_color=C_DEEP_GREEN, is_highlight=False):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = C_GOLD if is_highlight else border_color
        shape.line.width = Pt(1.5 if is_highlight else 1)

        tx_box = slide.shapes.add_textbox(left + Inches(0.24), top + Inches(0.2), width - Inches(0.48), height - Inches(0.4))
        tf = tx_box.text_frame
        tf.word_wrap = True

        if badge:
            p_badge = tf.paragraphs[0]
            p_badge.text = badge.upper()
            p_badge.font.size = Pt(9)
            p_badge.font.bold = True
            p_badge.font.color.rgb = C_GOLD if is_highlight else C_LEAF
            p_badge.space_after = Pt(4)
            p_title = tf.add_paragraph()
        else:
            p_title = tf.paragraphs[0]

        p_title.text = title
        p_title.font.size = Pt(15)
        p_title.font.bold = True
        p_title.font.color.rgb = title_color
        p_title.space_after = Pt(8)

        for it in items:
            p = tf.add_paragraph()
            p.text = f"• {it}" if not it.startswith("  ") else f"    {it}"
            p.font.size = Pt(11)
            p.font.color.rgb = C_SLATE_DARK
            p.space_after = Pt(5)

    # =========================================================================
    # SLIDE 1: COVER
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, C_DEEP_GREEN)

    # Logo Placement (Prominent)
    if active_logo and os.path.exists(active_logo):
        s1.shapes.add_picture(active_logo, Inches(0.9), Inches(1.1), Inches(1.3), Inches(1.3))

    s1_box = s1.shapes.add_textbox(Inches(0.9), Inches(2.6), Inches(11.5), Inches(3.2))
    tf1 = s1_box.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "AI-POWERED • VOICE-FIRST DIGITAL AGRICULTURAL ADVISORY"
    p0.font.size = Pt(11)
    p0.font.bold = True
    p0.font.color.rgb = C_GOLD
    p0.space_after = Pt(10)

    p1 = tf1.add_paragraph()
    p1.text = "Hello Farmer ሄሎ ፋርመር"
    p1.font.size = Pt(46)
    p1.font.bold = True
    p1.font.color.rgb = C_WHITE
    p1.space_after = Pt(8)

    p2 = tf1.add_paragraph()
    p2.text = "Agricultural intelligence, accessible through every farmer's voice."
    p2.font.size = Pt(22)
    p2.font.color.rgb = C_CREAM
    p2.space_after = Pt(8)

    p3 = tf1.add_paragraph()
    p3.text = "Breaking rural literacy, connectivity & linguistic barriers across Ethiopia via telephone voice & modern web."
    p3.font.size = Pt(14)
    p3.font.color.rgb = RGBColor(190, 212, 200)

    # Footer Metadata
    s1_foot = s1.shapes.add_textbox(Inches(0.9), Inches(6.0), Inches(11.5), Inches(1.0))
    tff = s1_foot.text_frame
    pf1 = tff.paragraphs[0]
    pf1.text = "Presenters: Yeabsira Girma • KalMesKeb • Yohannes Girma (jho-G)"
    pf1.font.size = Pt(12)
    pf1.font.bold = True
    pf1.font.color.rgb = C_WHITE
    pf2 = tff.add_paragraph()
    pf2.text = "Program / Context: UNDP & AI UniPod Innovation • October 2026"
    pf2.font.size = Pt(10.5)
    pf2.font.color.rgb = C_GOLD

    add_speaker_note(s1,
        "MAIN MESSAGE: Hello Farmer is an AI-powered, voice-first agricultural advisory platform built to give Ethiopian farmers immediate agronomic guidance in their native languages.\n\n"
        "SPOKEN EXPLANATION: Over 80% of Ethiopians depend on agriculture, but millions of smallholders cannot use conventional digital apps due to literacy, language, or connectivity constraints. Hello Farmer enables any farmer to simply pick up a phone or open a browser, ask an agricultural question in their mother tongue, and receive grounded, expert advice spoken aloud.\n\n"
        "TRANSITION: Let us look at the reality on the ground that makes this voice-first approach an urgent necessity."
    )

    # =========================================================================
    # SLIDE 2: THE PROBLEM
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2, C_CREAM)
    add_header(s2, "Agricultural Knowledge Is Inaccessible When Farmers Need It Most", "01 • THE PROBLEM")

    add_card(s2, Inches(0.9), Inches(1.8), Inches(2.7), Inches(4.9),
        "Access to Expertise",
        [
            "Farmers struggle to obtain timely advice when crop diseases strike.",
            "Extension agent ratios in rural woredas exceed 1 agent per 1,000+ farmers.",
            "Distance to agricultural bureaus delays critical interventions by days or weeks."
        ],
        badge="Challenge 01"
    )

    add_card(s2, Inches(3.8), Inches(1.8), Inches(2.7), Inches(4.9),
        "Language Barriers",
        [
            "Ethiopia is home to 80+ spoken languages and distinct scripts.",
            "Digital platforms heavily skew English or lack Ge'ez / Qubee support.",
            "Farmers need conversational guidance in Amharic, Afaan Oromo, Tigrinya, and Somali."
        ],
        badge="Challenge 02"
    )

    add_card(s2, Inches(6.7), Inches(1.8), Inches(2.7), Inches(4.9),
        "Digital & Literacy Divide",
        [
            "Over 65% of rural farming communities rely on basic 2G feature phones.",
            "High rural illiteracy renders text apps and complex SMS menus ineffective.",
            "Smartphones and mobile data cannot be assumed at the point of need."
        ],
        badge="Challenge 03"
    )

    add_card(s2, Inches(9.6), Inches(1.8), Inches(2.8), Inches(4.9),
        "Conventional Limitations",
        [
            "Existing hotlines face massive waiting queues and high abandonment rates.",
            "Rigid push-button IVR menus are frustrating for illiterate farmers.",
            "Static guidance fails to adapt to specific crop symptoms and localized weather."
        ],
        badge="Challenge 04"
    )

    add_speaker_note(s2,
        "MAIN MESSAGE: Ethiopia's agricultural knowledge gap is fundamentally an accessibility, linguistic, and literacy problem, not a lack of agronomic science.\n\n"
        "SPOKEN EXPLANATION: Imagine an Ethiopian smallholder noticing unexpected yellow streaks on their teff leaves. To get answers, they must wait for a rare extension visit or travel miles to the woreda center. Even if an SMS or app existed, reading technical text is impractical for many. Conventional IVR systems force them through confusing numeric menus. As a result, farmers misapply chemicals or wait too long, resulting in preventable crop loss.\n\n"
        "TRANSITION: Hello Farmer resolves this by meeting farmers exactly where they are—through natural voice."
    )

    # =========================================================================
    # SLIDE 3: THE SOLUTION
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3, C_WHITE)
    add_header(s3, "Ask Naturally. Receive Agricultural Guidance Through Your Voice.", "02 • THE SOLUTION")

    add_card(s3, Inches(0.9), Inches(1.8), Inches(5.6), Inches(4.9),
        "01 — Voice-First Telephone Hotline (8028)",
        [
            "Zero Smartphone / Zero Internet Required: Accessible from any standard 2G feature phone.",
            "Natural Conversational Interaction: Farmer speaks naturally without pressing keypad buttons.",
            "Real-Time Speech-to-Speech: Spoken question converted to text, reasoned over vetted manuals, and answered via neural voice.",
            "Post-Call SMS Summary: Dispatches structured, actionable reminders to the caller's phone."
        ],
        badge="Inclusive Telephony • Prototype Testing with Asterisk",
        is_highlight=True
    )

    add_card(s3, Inches(6.8), Inches(1.8), Inches(5.6), Inches(4.9),
        "02 — Modern Web Advisory Platform",
        [
            "End-to-End Browser Voice Chat: Interactive microphone recording, live transcription, and audio playback.",
            "Audio File Uploader: Allows farmers and testers to upload recorded voice notes without mic hardware.",
            "Hyperlocal Weather & Spray Risk Bar: Real-time spray-window safety analysis using Open-Meteo.",
            "Yield & Fertilizer Calculator: Calibrated for teff, maize, wheat, and barley using MoA ISFM recommendations.",
            "Extension Dashboard: Call tracking, symptom trend heatmaps, and outbound advisory SMS dispatch."
        ],
        badge="Connected Web App • Live at Localhost:3000"
    )

    add_speaker_note(s3,
        "MAIN MESSAGE: Hello Farmer operates a cohesive dual-channel product ecosystem anchored by a voice-first conversational AI agent.\n\n"
        "SPOKEN EXPLANATION: On Channel 1, rural farmers with standard button phones dial into a telephone interface, speak naturally, and hear vetted advice in Amharic or Afaan Oromo. On Channel 2, commercial growers, youth agripreneurs, and extension officers use our responsive web application for deeper insights, weather risk tracking, and yield calculations. Both channels share the exact same grounded agricultural AI core.\n\n"
        "TRANSITION: Let us see how a farmer experiences this interaction in practice."
    )

    # =========================================================================
    # SLIDE 4: PRODUCT DEMONSTRATION
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4, C_CREAM)
    add_header(s4, "From a Farmer's Question to Grounded Spoken Guidance", "03 • PRODUCT DEMONSTRATION")

    # Workflow Steps across top
    flow_steps = [
        ("1. Farmer Speaks", "Natural query via telephone or web mic"),
        ("2. Speech to Text", "Acoustic transcription to Ge'ez / Latin"),
        ("3. Knowledge RAG", "Retrieval from MoA ISFM manuals"),
        ("4. Safe Reasoning", "LLM reasoning + chemical guardrails"),
        ("5. Neural Voice", "Answer streamed aloud in Amharic/Oromo")
    ]
    card_w = Inches(2.2)
    for idx, (st_t, st_sub) in enumerate(flow_steps):
        l_pos = Inches(0.9) + idx * (card_w + Inches(0.12))
        add_card(s4, l_pos, Inches(1.8), card_w, Inches(1.5), st_t, [st_sub], badge=f"Step 0{idx+1}")

    # Concrete Demonstrable Example Box
    demo_box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(3.6), Inches(11.5), Inches(3.1))
    demo_box.fill.solid()
    demo_box.fill.fore_color.rgb = C_WHITE
    demo_box.line.color.rgb = C_CARD_BORDER
    demo_box.line.width = Pt(1)

    dtf = demo_box.text_frame
    dtf.word_wrap = True
    dp0 = dtf.paragraphs[0]
    dp0.text = "VERIFIED CONVERSATIONAL TURN (AMHARIC CROP FERTILIZATION QUERY)"
    dp0.font.size = Pt(10)
    dp0.font.bold = True
    dp0.font.color.rgb = C_LEAF
    dp0.space_after = Pt(6)

    dp1 = dtf.add_paragraph()
    dp1.text = "Farmer Spoken Voice (Input):"
    dp1.font.size = Pt(12)
    dp1.font.bold = True
    dp1.font.color.rgb = C_DEEP_GREEN

    dp2 = dtf.add_paragraph()
    dp2.text = "“የጤፍ ሰብል ምርታማነትን ለመጨመር ምን ዓይነት ማዳበሪያ መጠቀም አለብኝ?” (What fertilizer should I use to increase teff yield?)"
    dp2.font.size = Pt(13)
    dp2.font.italic = True
    dp2.font.color.rgb = C_SLATE_DARK
    dp2.space_after = Pt(8)

    dp3 = dtf.add_paragraph()
    dp3.text = "Hello Farmer AI Spoken Guidance (Output):"
    dp3.font.size = Pt(12)
    dp3.font.bold = True
    dp3.font.color.rgb = C_DEEP_GREEN

    dp4 = dtf.add_paragraph()
    dp4.text = "“ለጤፍ ሰብል በመስክ መመሪያው መሠረት በዘር ወቅት NPS ማዳበሪያ በሄክታር 100 ኪ.ግ መጠቀም ይመረጣል። ዩሪያ ማዳበሪያ ደግሞ በሁለት ዙር ተከፍሎ—በመጀመሪያው አረም ወቅት እና ሰብሉ በሚያድግበት ወቅት መሰጠት አለበት። የአፈርዎን ዓይነት ማረጋገጥዎን አይርሱ።”"
    dp4.font.size = Pt(12)
    dp4.font.color.rgb = C_SLATE_DARK
    dp4.space_after = Pt(4)

    dp5 = dtf.add_paragraph()
    dp5.text = "Grounded Sources: Ethiopia Ministry of Agriculture (MoA) ISFM Field Guide • Latency: < 1.8s • Audio Format: 8kHz PCM Telephony & 24kHz Web Audio"
    dp5.font.size = Pt(9.5)
    dp5.font.bold = True
    dp5.font.color.rgb = C_GOLD

    add_speaker_note(s4,
        "MAIN MESSAGE: The entire interaction from spoken question to spoken answer is grounded in verified Ministry of Agriculture recommendations and executes in under 2 seconds.\n\n"
        "SPOKEN EXPLANATION: Here is an actual interaction demonstrated on our working prototype. A farmer asks in Amharic how to maximize teff yield. The Gemini/Whisper STT transcribes the audio into Ge'ez script. The RAG pipeline searches our pgvector database of verified Ethiopian ISFM field guides. The Groq Qwen-2.5-32B engine crafts the response, guardrails verify there is no dangerous guidance, and Edge Neural TTS speaks the vetted answer back to the farmer.\n\n"
        "TRANSITION: Behind this effortless conversation lies a purpose-built AI architecture."
    )

    # =========================================================================
    # SLIDE 5: HOW IT WORKS (ARCHITECTURE)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5, C_WHITE)
    add_header(s5, "A Conversational AI System Built Around the Farmer's Voice", "04 • HOW IT WORKS")

    add_card(s5, Inches(0.9), Inches(1.8), Inches(3.6), Inches(4.9),
        "Speech Recognition (STT)",
        [
            "Multimodal Gemini Audio STT: Transcribes telephone 8kHz PCM and web 16kHz audio directly to Amharic and Afaan Oromo.",
            "Groq Whisper Large-v3: Sub-second cloud ASR running on Groq LPUs.",
            "Local HuggingFace Whisper & Meta MMS: Fully offline acoustic fallback for edge deployments.",
            "Energy-Based VAD: Automatic silence detection and barge-in support."
        ],
        badge="Layer 01 • Acoustic Processing"
    )

    add_card(s5, Inches(4.8), Inches(1.8), Inches(3.6), Inches(4.9),
        "Cognitive Core & RAG",
        [
            "PostgreSQL 16 pgvector DB: Stores verified Ethiopian Ministry of Agriculture ISFM field guides.",
            "Multilingual Embeddings: Gemini text-embedding-004 and BAAI/bge-m3 dense vectors.",
            "Groq Qwen-2.5-32B Engine: Ultra-low latency conversational reasoning.",
            "Agricultural Guardrails: Validates dosage limits and intercepts banned chemicals before generation."
        ],
        badge="Layer 02 • Grounded Reasoning"
    )

    add_card(s5, Inches(8.8), Inches(1.8), Inches(3.6), Inches(4.9),
        "Voice Delivery & Services",
        [
            "Microsoft Edge Neural TTS: Expressive Ethiopian Amharic voices (Mekdes & Ameha).",
            "Asterisk AudioSocket: Bidirectional raw PCM streaming over telephone channels.",
            "Open-Meteo Weather Risk API: Live wind, rain & humidity spraying analysis.",
            "Asynchronous Arq Worker: Manages follow-up SMS advisory dispatch via Redis."
        ],
        badge="Layer 03 • Synthesis & Telephony"
    )

    add_speaker_note(s5,
        "MAIN MESSAGE: Our architecture is designed for speed, grounded accuracy, and offline resilience, avoiding generic unconstrained chatbot hallucinations.\n\n"
        "SPOKEN EXPLANATION: We decouple the voice pipeline into three clear layers. First, acoustic processing converts raw audio into text with Voice Activity Detection. Second, our cognitive layer passes the query through vector search against vetted Ministry of Agriculture documents—meaning the AI cannot invent dangerous pesticide dosages. Third, neural voice synthesis streams natural Ethiopian voices back to the user. Supporting microservices handle weather risk analysis and SMS dispatch.\n\n"
        "TRANSITION: Who are the target users who benefit from this architecture?"
    )

    # =========================================================================
    # SLIDE 6: TARGET USERS AND MARKET OPPORTUNITY
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6, C_CREAM)
    add_header(s6, "One Agricultural AI Platform, Designed for Diverse Farmers", "05 • TARGET USERS & MARKET")

    add_card(s6, Inches(0.9), Inches(1.8), Inches(2.7), Inches(4.9),
        "Smallholder Farmers",
        [
            "Over 16+ million smallholder farm households in Ethiopia.",
            "Primary users of the voice hotline 8028 via standard 2G button phones.",
            "Require immediate spoken advice on fertilizer timing, pest identification, and planting depth."
        ],
        badge="Primary Beneficiaries"
    )

    add_card(s6, Inches(3.8), Inches(1.8), Inches(2.7), Inches(4.9),
        "Commercial Farmers",
        [
            "Commercial growers in Oromia, Amhara, and Sidama regions.",
            "Utilize the web dashboard for weather spraying risk, teff/maize yield calculations, and SMS alerts.",
            "Willingness to pay for advanced agronomic optimization and soil tracking."
        ],
        badge="Commercial Market"
    )

    add_card(s6, Inches(6.7), Inches(1.8), Inches(2.7), Inches(4.9),
        "Youth Agripreneurs",
        [
            "Young Ethiopians entering horticulture, poultry, and modern farming.",
            "Digitally savvy, smartphone-enabled, seeking validated agricultural business insights.",
            "Bridge generational farming knowledge gaps."
        ],
        badge="Emerging Innovators"
    )

    add_card(s6, Inches(9.6), Inches(1.8), Inches(2.8), Inches(4.9),
        "Institutional Partners",
        [
            "Ministry of Agriculture (MoA), ATA/ATI, and regional agricultural bureaus.",
            "NGOs, FAO, and development programs seeking scalable outreach channels.",
            "Co-operatives and input suppliers seeking verifiable advisory distribution."
        ],
        badge="Distribution Partners"
    )

    add_speaker_note(s6,
        "MAIN MESSAGE: Hello Farmer serves both underserved rural smallholders who need simple voice access and modern commercial growers who want data-driven web tools.\n\n"
        "SPOKEN EXPLANATION: We segment our market into four distinct tiers. Smallholders represent our largest social impact group—over 16 million households reached via voice hotline 8028 without requiring internet. Commercial farmers and young agripreneurs represent our early commercial adoption group through web and SMS tools. Finally, institutional partners like the Ministry of Agriculture and agricultural development agencies represent our deployment and scaling partners.\n\n"
        "TRANSITION: How does Hello Farmer compare against existing alternatives in the market?"
    )

    # =========================================================================
    # SLIDE 7: DIFFERENTIATION
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7, C_WHITE)
    add_header(s7, "Voice-First Access, Local-Language Focus, Grounded Science", "06 • DIFFERENTIATION")

    add_card(s7, Inches(0.9), Inches(1.8), Inches(2.7), Inches(4.9),
        "Traditional Extension",
        [
            "Human Expertise: Highly trusted by local farmers.",
            "Limited Capacity: Ratio often 1 DA to 1,000+ farmers.",
            "Delayed Response: Physically impossible to handle sudden regional outbreaks.",
            "High Operating Cost: Requires continuous travel and field expenses."
        ],
        badge="Conventional Advisory"
    )

    add_card(s7, Inches(3.8), Inches(1.8), Inches(2.7), Inches(4.9),
        "Traditional IVR (8028)",
        [
            "Phone Accessible: Operates on feature phones.",
            "Rigid Numeric Menus: Press 1 for Maize, Press 2 for Wheat.",
            "Zero Conversational Flexibility: Cannot diagnose multi-symptom descriptions.",
            "High Drop-off: Complex tree navigation frustrates illiterate callers."
        ],
        badge="Static Telephone IVR"
    )

    add_card(s7, Inches(6.7), Inches(1.8), Inches(2.7), Inches(4.9),
        "General-Purpose AI",
        [
            "Broad Conversational Power: Fluent text in common world languages.",
            "Hallucination Risk: Generates incorrect chemical dosages without grounding.",
            "Requires Internet & Smartphone: Excludes 65%+ of rural smallholders.",
            "Poor Ethiopian Language Speech: Lacks natural Amharic/Oromo neural voice."
        ],
        badge="Generic Chatbots"
    )

    add_card(s7, Inches(9.6), Inches(1.8), Inches(2.8), Inches(4.9),
        "Hello Farmer",
        [
            "Voice-First & Natural: Speaks native Amharic & Afaan Oromo conversationally.",
            "RAG-Grounded: Strict adherence to Ministry of Agriculture ISFM manuals.",
            "Dual Channel: Runs on simple feature phones AND modern web browsers.",
            "Safety Guardrails: Active weather spray validation & chemical limits."
        ],
        badge="Hello Farmer Advantage",
        is_highlight=True
    )

    add_speaker_note(s7,
        "MAIN MESSAGE: Hello Farmer is not another generic chatbot; it unites phone accessibility, local language speech AI, and strict agricultural grounding.\n\n"
        "SPOKEN EXPLANATION: Compared to traditional extension workers who are overwhelmed, Hello Farmer provides 24/7 instant access. Compared to conventional push-button IVR hotlines, our system lets farmers speak in full natural sentences. And unlike generic AI chatbots like ChatGPT which require smartphones and often hallucinate unsafe chemical doses, Hello Farmer is strictly grounded in Ministry of Agriculture manuals and speaks through standard phones.\n\n"
        "TRANSITION: How do we measure whether this system is truly delivering value to farmers?"
    )

    # =========================================================================
    # SLIDE 8: IMPACT AND MEASUREMENT
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8, C_CREAM)
    add_header(s8, "Success Means More Than Answering Questions", "07 • IMPACT & EVALUATION")

    add_card(s8, Inches(0.9), Inches(1.8), Inches(3.6), Inches(4.9),
        "Level 1: Inclusive Access",
        [
            "Universal Digital Access: Breaking the requirement for smartphones and high literacy.",
            "Linguistic Equity: Native conversational support in Amharic and Afaan Oromo.",
            "24/7 Availability: Advice during critical evening and early morning farming hours."
        ],
        badge="Immediate Impact"
    )

    add_card(s8, Inches(4.8), Inches(1.8), Inches(3.6), Inches(4.9),
        "Level 2: Decision Support",
        [
            "Preventing Chemical Poisoning: Elimination of banned substance recommendations.",
            "Weather-Synchronized Spraying: Minimizing spray wash-off and wind drift.",
            "Precision Nutrient Timing: Calibrated split Urea & NPS fertilizer applications."
        ],
        badge="Actionable Impact"
    )

    add_card(s8, Inches(8.8), Inches(1.8), Inches(3.6), Inches(4.9),
        "Level 3: Long-Term Resilience",
        [
            "Yield Protection: Mitigating pest damage through rapid early symptom identification.",
            "Community Data Intelligence: Real-time woreda-level disease outbreak tracking.",
            "Food Security: Strengthening smallholder economic stability across rural Ethiopia."
        ],
        badge="Systemic Impact"
    )

    add_speaker_note(s8,
        "MAIN MESSAGE: Our planned evaluation framework measures real-world farmer outcomes across access, decision quality, and long-term yield resilience.\n\n"
        "SPOKEN EXPLANATION: We do not measure success simply by server calls or tokens generated. We evaluate our platform on three distinct levels. At the access level, we track call completion rates, WER across dialects, and linguistic inclusivity. At the decision level, we measure safety adherence and expert-rated answer relevance. At the systemic level, we track whether farmers avoided crop losses through timely spray and fertilizer guidance.\n\n"
        "TRANSITION: How will Hello Farmer sustain its operations financially over the long term?"
    )

    # =========================================================================
    # SLIDE 9: BUSINESS MODEL AND SUSTAINABILITY
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9, C_WHITE)
    add_header(s9, "A Pathway to Sustainable Digital Agricultural Advisory", "08 • BUSINESS MODEL")

    add_card(s9, Inches(0.9), Inches(1.8), Inches(5.6), Inches(2.35),
        "Institutional Service Agreements",
        [
            "B2G & NGO Contracts: Sponsored hotline capacity funded by development partners (UNDP, FAO, USAID) and the Ministry of Agriculture to serve designated woredas."
        ],
        badge="Revenue Stream 01"
    )

    add_card(s9, Inches(0.9), Inches(4.35), Inches(5.6), Inches(2.35),
        "Agribusiness & Cooperative Partnerships",
        [
            "Seed & Fertilizer Value Chains: Agricultural unions sponsor branded voice advisory services to ensure farmers apply their inputs correctly, reducing crop failure."
        ],
        badge="Revenue Stream 02"
    )

    add_card(s9, Inches(6.8), Inches(1.8), Inches(5.6), Inches(2.35),
        "Commercial & Premium Web Services",
        [
            "Freemium Web Subscriptions: Tiered access for commercial farms, offering advanced soil telemetry, multi-field analytics, and automated SMS alert packages."
        ],
        badge="Revenue Stream 03"
    )

    add_card(s9, Inches(6.8), Inches(4.35), Inches(5.6), Inches(2.35),
        "Lean Cost Structure",
        [
            "SIP Telephony & AudioSocket: Highly optimized, caching fixed prompts to slash dynamic TTS costs.",
            "Local Offline Fallback: Ollama and local Whisper enable zero-cloud deployment for rural stations."
        ],
        badge="Operational Efficiency"
    )

    add_speaker_note(s9,
        "MAIN MESSAGE: Hello Farmer balances free, equitable farmer access with institutional and B2B revenue models to guarantee long-term financial sustainability.\n\n"
        "SPOKEN EXPLANATION: Smallholders should never be charged for critical agricultural guidance. Instead, we model our sustainability on institutional service agreements with agricultural agencies, NGO development programs, and agricultural cooperatives who already invest heavily in extension outreach. For commercial growers, our advanced web tools offer a recurring subscription model, while our hybrid offline/cloud architecture keeps per-minute inference costs extraordinarily low.\n\n"
        "TRANSITION: Where does the project stand today, and what are the immediate milestones ahead?"
    )

    # =========================================================================
    # SLIDE 10: CURRENT PROGRESS AND ROADMAP
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10, C_CREAM)
    add_header(s10, "From Prototype to Validated National Farmer Service", "09 • PROGRESS & ROADMAP")

    add_card(s10, Inches(0.9), Inches(1.8), Inches(3.6), Inches(4.9),
        "BUILT & VERIFIED",
        [
            "End-to-End Voice Chat in Web App with instant transcription and spoken audio playback.",
            "Local Telephony PBX (Asterisk) container with AudioSocket streaming application.",
            "Grounded Knowledge Base (RAG) with pgvector, MoA ISFM guides, and Gemini/BGE embeddings.",
            "Yield Calculator and Weather Risk Bar active across Ethiopian cities.",
            "8/8 Automated Integration Test Suite passing inside Docker containers."
        ],
        badge="Completed Milestones",
        is_highlight=True
    )

    add_card(s10, Inches(4.8), Inches(1.8), Inches(3.6), Inches(4.9),
        "IN PROGRESS",
        [
            "Fine-Tuning Amharic Dialect STT Models in dedicated amharic-stt-2 repository.",
            "Extending Afaan Oromo speech recognition dataset and local voice models.",
            "Refining agricultural safety guardrails against regional banned chemicals.",
            "Conducting internal agricultural expert review with vetted agronomy rubrics."
        ],
        badge="Active Development"
    )

    add_card(s10, Inches(8.8), Inches(1.8), Inches(3.6), Inches(4.9),
        "NEXT (ROADMAP)",
        [
            "Controlled Field Pilot: 100-farmer trial in Oromia & Amhara regions.",
            "Formal Telecom Trunking: Securing official Ethio Telecom shortcode integration.",
            "Agricultural Research Review: Formal partnership with Ethiopian Institute of Agricultural Research (EIAR).",
            "Computer Vision Extension: Smartphone leaf disease photo diagnosis."
        ],
        badge="Future Milestones"
    )

    add_speaker_note(s10,
        "MAIN MESSAGE: Hello Farmer is a working, demonstrable engineering prototype with a clear, realistic roadmap toward institutional field deployment.\n\n"
        "SPOKEN EXPLANATION: We maintain complete transparency about our status. Today, our end-to-end voice pipeline, web interface, Asterisk telephony testbed, and RAG knowledge base are fully built, passing all 8 automated integration tests. In active progress, we are fine-tuning acoustic models for regional Amharic dialects. Our next phase is a controlled 100-farmer pilot to validate response accuracy and user experience under real field conditions.\n\n"
        "TRANSITION: Who is the team driving this technical execution?"
    )

    # =========================================================================
    # SLIDE 11: TEAM AND PARTNERSHIPS
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11, C_WHITE)
    add_header(s11, "Combining AI Engineering with Agricultural Domain Expertise", "10 • TEAM & CAPABILITIES")

    add_card(s11, Inches(0.9), Inches(1.8), Inches(3.6), Inches(4.9),
        "Engineering Team",
        [
            "Yeabsira Girma (YEAB-G): AI Systems, Full-Stack Architecture & Speech Processing.",
            "KalMesKeb: Backend Systems, Telephony Engineering & Data Pipelines.",
            "Yohannes Girma (jho-G): Full-Stack Web Development, UI/UX & Deployment.",
            "Hands-on experience in full-stack speech pipelines, Docker microservices, and NLP."
        ],
        badge="Core Contributors"
    )

    add_card(s11, Inches(4.8), Inches(1.8), Inches(3.6), Inches(4.9),
        "Interdisciplinary Needs",
        [
            "Agronomic Validation: Ongoing review with certified Ethiopian agricultural extension specialists.",
            "Linguistic Evaluation: Native speech dataset curators for Afaan Oromo and regional Amharic dialects.",
            "Field UX Researchers: Human-centered design testing directly in rural farming woredas."
        ],
        badge="Advisory Expertise"
    )

    add_card(s11, Inches(8.8), Inches(1.8), Inches(3.6), Inches(4.9),
        "Institutional Alignment",
        [
            "AI UniPod & UNDP Ethiopia: Innovation ecosystem backing and incubation support.",
            "Ministry of Agriculture (MoA): Alignment with national digital agriculture strategies.",
            "Agricultural Research Centers: Collaborative knowledge evaluation with EIAR researchers."
        ],
        badge="Ecosystem Partners"
    )

    add_speaker_note(s11,
        "MAIN MESSAGE: Our engineering team has built a working prototype and is actively assembling the agricultural and institutional partnerships needed for field success.\n\n"
        "SPOKEN EXPLANATION: Successful digital agriculture requires both strong software engineering and rigorous agronomic ground-truth. Our core team has demonstrated technical execution by building the telephony, speech, and RAG architecture. We are now collaborating with agricultural researchers, native linguists, and ecosystem partners like AI UniPod and UNDP to ensure our guidance is rigorous, safe, and regionally calibrated.\n\n"
        "TRANSITION: What specific support are we seeking to take Hello Farmer into the field?"
    )

    # =========================================================================
    # SLIDE 12: THE ASK
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12, C_DEEP_GREEN)

    # Logo prominent
    if active_logo and os.path.exists(active_logo):
        s12.shapes.add_picture(active_logo, Inches(0.9), Inches(0.9), Inches(1.1), Inches(1.1))

    s12_box = s12.shapes.add_textbox(Inches(0.9), Inches(2.2), Inches(11.5), Inches(4.8))
    tf12 = s12_box.text_frame
    tf12.word_wrap = True

    p0 = tf12.paragraphs[0]
    p0.text = "PARTNERSHIP & PILOT VALIDATION"
    p0.font.size = Pt(11)
    p0.font.bold = True
    p0.font.color.rgb = C_GOLD
    p0.space_after = Pt(8)

    p1 = tf12.add_paragraph()
    p1.text = "Help Us Make Agricultural Knowledge Accessible to Every Farmer"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = C_WHITE
    p1.space_after = Pt(14)

    p2 = tf12.add_paragraph()
    p2.text = "We are seeking strategic support across four priority areas:"
    p2.font.size = Pt(14)
    p2.font.bold = True
    p2.font.color.rgb = C_CREAM
    p2.space_after = Pt(8)

    p3 = tf12.add_paragraph()
    p3.text = "1. Pilot Funding & Compute Support: Cloud inference & telecom trunking for a controlled 100-farmer woreda trial [INSERT TARGET AMOUNT]."
    p3.font.size = Pt(12.5)
    p3.font.color.rgb = RGBColor(220, 235, 226)
    p3.space_after = Pt(4)

    p4 = tf12.add_paragraph()
    p4.text = "2. Field Pilot Access: Partnerships with agricultural cooperatives or development projects in Oromia & Amhara."
    p4.font.size = Pt(12.5)
    p4.font.color.rgb = RGBColor(220, 235, 226)
    p4.space_after = Pt(4)

    p5 = tf12.add_paragraph()
    p5.text = "3. Agronomic Review: Formal review collaboration with EIAR and Ministry of Agriculture agronomists."
    p5.font.size = Pt(12.5)
    p5.font.color.rgb = RGBColor(220, 235, 226)
    p5.space_after = Pt(4)

    p6 = tf12.add_paragraph()
    p6.text = "4. Speech AI Research: Collaborative speech dataset sharing for underrepresented Ethiopian languages."
    p6.font.size = Pt(12.5)
    p6.font.color.rgb = RGBColor(220, 235, 226)
    p6.space_after = Pt(14)

    p7 = tf12.add_paragraph()
    p7.text = "“Hello Farmer aims to make agricultural knowledge accessible by allowing farmers to ask questions naturally in their own languages. With technical validation, agricultural partnerships, and farmer-centered testing, we can build a truly inclusive pathway for Ethiopian agriculture.”"
    p7.font.size = Pt(12)
    p7.font.italic = True
    p7.font.color.rgb = C_GOLD
    p7.space_after = Pt(10)

    p8 = tf12.add_paragraph()
    p8.text = "Contact: team@hellofarmer.et • Project Repo: github.com/jho-G/Hello-Farmer • Addis Ababa, Ethiopia"
    p8.font.size = Pt(11)
    p8.font.color.rgb = C_WHITE

    add_speaker_note(s12,
        "MAIN MESSAGE: With pilot funding, field community access, and agronomic review, we will transform Hello Farmer from a verified technical prototype into an impactful national advisory service.\n\n"
        "SPOKEN EXPLANATION: We have demonstrated that the voice technology works. To take this from local prototype to real-world impact, we need the support of partners who care about inclusive digital agriculture. We are seeking pilot support to fund telecom connectivity and compute for a 100-farmer trial, access to rural pilot farming communities, and collaboration with agricultural experts to review our answers. Together, we can ensure every Ethiopian farmer has access to knowledge through their voice.\n\n"
        "TRANSITION: Thank you. We now welcome questions and are ready to present the live prototype."
    )

    # =========================================================================
    # APPENDIX SLIDES (10 BACKUP SLIDES)
    # =========================================================================
    appendix_data = [
        ("A1 • Detailed Technical Architecture", "Microservices & Telephony Deep Dive", [
            "Asterisk PBX: AudioSocket application bridge streaming bidirectional 8kHz 16-bit linear PCM audio over TCP sockets.",
            "FastAPI Backend: Asynchronous REST and AudioSocket server orchestrating STT, RAG, LLM, and TTS pipelines.",
            "PostgreSQL 16 with pgvector: Stores chunked agronomic knowledge with cosine similarity vector indexes.",
            "Redis 7 & Arq Worker: Manages call state caching, rate limiting, and asynchronous SMS dispatch queues.",
            "Docker Compose Deployment: 6 container services with containerized health checks and resource limits."
        ]),
        ("A2 • Implementation Verification Matrix", "Verified vs In-Progress vs Planned Features", [
            "VERIFIED & DEMONSTRABLE: End-to-end web voice chat, audio file upload, RAG vector retrieval, Asterisk AudioSocket telephony testing, weather risk analysis, yield calculator, 8/8 automated test suite.",
            "PARTIALLY IMPLEMENTED / TESTING: Afaan Oromo speech recognition, caller privacy salt rotation, live Asterisk SIP call simulation with MicroSIP.",
            "PLANNED / VALIDATION NEEDED: Public telecom shortcode trunking, commercial payment integration, camera-based pest vision diagnostics.",
            "NOTE: Architecture components are strictly separated from production deployment status."
        ]),
        ("A3 • Speech Recognition Benchmarking", "Methodology for Underrepresented Languages", [
            "Dual Testing Pipeline: Gemini Audio multimodal STT compared against Groq Whisper Large-v3 and Meta MMS.",
            "Acoustic Degradation: Testing resilience under 8kHz telephone compression and ambient farm background noise (tractors, wind, livestock).",
            "Custom Dialect Fine-Tuning: Active acoustic training in amharic-stt-2 repository addressing regional accents (Wollo, Gojjam, Shewa).",
            "Evaluation Metric: Target Word Error Rate (WER) < 18% on specialized Ethiopian agronomic terminology."
        ]),
        ("A4 • Knowledge Grounding & Safety Strategy", "Mitigating Hallucination in Critical Guidance", [
            "Source Curation: Ethiopia Ministry of Agriculture Integrated Soil Fertility Management (ISFM) and crop protection field guides.",
            "Deterministic Safety Guardrails: Hard intercept rules prohibiting banned substances (e.g. DDT, Aldrin, Endosulfan).",
            "Strict Dosage Clamping: Chemical concentrations and pre-harvest intervals (PHI) clamped to official guidelines.",
            "Low-Confidence Safeguard: Automatically falls back to 'Consult your local Development Agent' when similarity score < 0.65."
        ]),
        ("A5 • Market Sizing Methodology & Demographics", "Data-Backed Assumptions for Ethiopia", [
            "Total Addressable Market (TAM): ~16.5M agricultural households in Ethiopia (Central Statistical Agency / FAO data).",
            "Serviceable Addressable Market (SAM): ~11M farmers within mobile network coverage areas (Ethio Telecom 2G/3G footprint).",
            "Serviceable Obtainable Market (SOM): Initial target of 50,000 farmers across high-potential agrarian woredas in Oromia & Amhara during Phase 1-2.",
            "Key Distinction: Smallholders represent social impact beneficiaries; agribusinesses and development agencies represent paying sponsors."
        ]),
        ("A6 • Pilot Budget & Operating Cost Assumptions", "100-Farmer Controlled Field Trial", [
            "Cloud Inference (STT, LLM, TTS): Estimated at ~$0.012 per minute of active voice advisory conversation.",
            "Telecom Inbound Toll-Free SIP Trunking: Estimated pilot allocation [INSERT QUOTE FROM ETHIO TELECOM].",
            "Agronomic Expert Review & Honoraria: 2 certified agronomists reviewing 500 conversation transcripts.",
            "Field Logistics & Farmer Onboarding: 4 enumerators conducting pre/post pilot usability and harvest surveys.",
            "Total Pilot Budget Requirement: [INSERT VERIFIED PILOT BUDGET FIGURE]."
        ]),
        ("A7 • Competitive Alternatives Deep Dive", "Comparative Analysis Across African Agri-Tech", [
            "National ATA 8028 Hotline: Established reach, but limited by static numeric push-button IVR menus without conversational reasoning.",
            "SMS Advisory Services (e.g., 8-0-2-8 text): Ineffective for illiterate smallholders; text cannot capture nuanced multi-symptom descriptions.",
            "Regional Mobile Apps: Require smartphones and 4G connectivity; heavily biased toward English or urban users.",
            "Hello Farmer Moat: Conversational voice in local languages + strict agricultural grounding + dual phone/web accessibility."
        ]),
        ("A8 • Privacy, Consent & Data Governance", "Protecting Vulnerable Rural Callers", [
            "Salted Caller Hashing: Raw telephone numbers are immediately hashed with SHA-256 and rotating secret salt—never stored in plain text.",
            "Pseudonymous Analytics: Call history and symptom analytics link to caller hashes, preventing PII leakage.",
            "Explicit Caller Consent: First-time callers receive an audio prompt requesting permission to store question context for service improvement.",
            "Data Sovereignty: Database architecture designed for local hosting within Ethiopia-compliant infrastructure."
        ]),
        ("A9 • Risk Assessment & Mitigation Matrix", "Anticipating Operational & Technical Challenges", [
            "Risk 1: Telecom Trunking Delays -> Mitigation: Maintain web voice interface and local Asterisk SIP testing testbeds.",
            "Risk 2: Dialect Speech Recognition Drop -> Mitigation: Active fine-tuning on regional Ethiopian accents; fallback to human extension review.",
            "Risk 3: Model Hallucination -> Mitigation: Pre-generation vector grounding + post-generation deterministic chemical guardrails.",
            "Risk 4: Farmer Skepticism -> Mitigation: Partner with trusted local Development Agents (DAs) and agricultural cooperatives."
        ]),
        ("A10 • Pilot Milestones & Evaluation Criteria", "Phase-by-Phase Roadmap to Validation", [
            "Phase 1 (Months 1-2): Laboratory benchmark testing; 500 simulated multi-dialect calls; expert agronomic review.",
            "Phase 2 (Months 3-4): 100-farmer controlled field trial in selected Oromia and Amhara woredas; usability and WER measurement.",
            "Phase 3 (Months 5-6): Impact analysis; measure advice adoption, chemical safety compliance, and user satisfaction.",
            "Key Success Criteria: >85% task completion rate; <15% WER on agricultural terms; zero unsafe chemical recommendations."
        ]),
    ]

    for app_idx, (app_title, app_subtitle, app_bullets) in enumerate(appendix_data):
        sa = prs.slides.add_slide(blank_layout)
        set_slide_background(sa, C_CREAM)
        add_header(sa, app_title, f"APPENDIX • TECHNICAL BACKUP {app_idx+1}/10")

        add_card(sa, Inches(0.9), Inches(1.8), Inches(11.5), Inches(4.9),
            app_subtitle,
            app_bullets,
            badge="Technical Specification & Methodology"
        )

        add_speaker_note(sa,
            f"APPENDIX NOTE ({app_title}): This backup slide provides technical reviewers, agronomists, and investors with the detailed methodology, architecture, and verification data supporting the main presentation deck."
        )

    # Save PPTX
    prs.save(pptx_path)
    print(f"[PPTX] Pitch deck saved successfully: {pptx_path} (Total Slides: {len(prs.slides)})")

    # Generate Companion PDF
    build_pdf_companion(pdf_path)

def build_pdf_companion(pdf_path="Hello_Farmer_Pitch_Deck.pdf"):
    """Builds a high-quality executive PDF matching the pitch deck layout."""
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=landscape(letter),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=r_colors.HexColor('#103729')
    )
    subtitle_style = ParagraphStyle(
        'CoverSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        textColor=r_colors.HexColor('#174B35')
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=r_colors.HexColor('#103729')
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=r_colors.HexColor('#202923')
    )
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=r_colors.HexColor('#202923')
    )

    story = []

    # Cover Page in PDF
    story.append(Paragraph("Hello Farmer | ሄሎ ፋርመር", title_style))
    story.append(Paragraph("Agricultural intelligence, accessible through every farmer's voice.", subtitle_style))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("AI-Powered, Voice-First Agricultural Advisory Platform for Ethiopia • UNDP & AI UniPod Context", body_style))
    story.append(Paragraph("Presenters: Yeabsira Girma • KalMesKeb • Yohannes Girma (jho-G) • October 2026", body_style))
    story.append(Spacer(1, 0.3 * inch))

    # Executive Summary Table
    summary_data = [
        [
            Paragraph("<b>01 • The Problem</b><br/>Over 80% of Ethiopians rely on agriculture. Rural smallholders face severe expertise shortages, linguistic exclusion, high illiteracy, and rigid push-button IVR menus.", bullet_style),
            Paragraph("<b>02 • The Solution</b><br/>Inclusive Dual-Channel AI: (1) Voice-first telephone hotline (8028) on simple 2G feature phones; (2) Web app with voice chat, weather spraying risk, and yield calculator.", bullet_style)
        ],
        [
            Paragraph("<b>03 • Working Architecture</b><br/>Acoustic processing (Gemini Audio / Groq Whisper STT) ➔ RAG Vector DB (pgvector with MoA ISFM field manuals) ➔ Groq Qwen-2.5-32B ➔ Edge Neural TTS (Amharic Mekdes/Ameha).", bullet_style),
            Paragraph("<b>04 • Safety & Grounding</b><br/>Strict deterministic chemical guardrails block banned substances (e.g. DDT). Real-time Open-Meteo weather integration prevents pesticide wash-off and wind drift.", bullet_style)
        ],
        [
            Paragraph("<b>05 • Progress & Milestones</b><br/>End-to-end voice chat active in web app. Asterisk PBX AudioSocket telephony testing operational. 8/8 automated integration tests verified. Dialect fine-tuning in progress.", bullet_style),
            Paragraph("<b>06 • The Ask</b><br/>Seeking pilot compute & telecom funding, access to 100-farmer pilot communities in Oromia & Amhara, and agronomic review partnerships with EIAR and Ministry of Agriculture.", bullet_style)
        ]
    ]

    t = Table(summary_data, colWidths=[4.9 * inch, 4.9 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), r_colors.HexColor('#F7F5EC')),
        ('BOX', (0, 0), (-1, -1), 1, r_colors.HexColor('#E2E8E4')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, r_colors.HexColor('#E2E8E4')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("<b>Complete 22-Slide Pitch Deck Structure:</b>", section_style))
    story.append(Paragraph("• <b>Main Slides (1-12):</b> Cover ➔ Problem ➔ Solution ➔ Product Demo ➔ How It Works ➔ Target Users & Market ➔ Differentiation ➔ Impact & Metrics ➔ Business Model ➔ Current Progress & Roadmap ➔ Team ➔ The Ask.<br/>• <b>Technical Appendix (A1-A10):</b> Telephony Architecture, Feature Matrix, STT Benchmarking, Knowledge Safety, Market Sizing, Pilot Budget, Alternatives Deep Dive, Privacy & Consent, Risk Matrix, Pilot Milestones.", body_style))

    doc.build(story)
    print(f"[PDF] Executive presentation companion saved: {pdf_path}")

if __name__ == "__main__":
    out_pptx = sys.argv[1] if len(sys.argv) > 1 else "Hello_Farmer_Pitch_Deck.pptx"
    out_pdf = sys.argv[2] if len(sys.argv) > 2 else "Hello_Farmer_Pitch_Deck.pdf"
    build_pitch_deck(out_pptx, out_pdf)
